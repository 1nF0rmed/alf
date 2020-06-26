# Copyright (c) 2020 Horizon Robotics. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""HyperNetwork algorithm."""

from absl import logging
import gin
import torch
import torch.nn.functional as F
from tqdm import tqdm
from typing import Callable

import alf
from alf.data_structures import AlgStep, LossInfo, namedtuple
from alf.algorithms.generator import Generator
from alf.algorithms.hypernetwork_networks import ParamNetwork
from alf.networks import EncodingNetwork
from alf.tensor_specs import TensorSpec
from alf.utils import common, math_ops
from alf.utils.summary_utils import record_time

HyperNetworkLossInfo = namedtuple("HyperNetworkLossInfo",
                                  ["loss", "acc", "avg_acc"])


@gin.configurable
class HyperNetwork(Generator):
    """HyperNetwork

    """

    def __init__(
            self,
            input_tensor_spec,
            conv_layer_params=None,
            fc_layer_params=None,
            activation=torch.relu_,
            last_layer_size=None,
            last_activation=None,
            noise_dim=32,
            # noise_type='normal',
            hidden_layers=(64, 64),
            use_fc_bn=False,
            particles=32,
            entropy_regularization=1.,
            kernel_sharpness=2.,
            loss_func: Callable = None,
            optimizer=None,
            regenerate_for_each_batch=True,
            name="HyperNetwork"):
        """
        Args:
            Args for the generated parametric network
            ====================================================================
            input_tensor_spec (nested TensorSpec): the (nested) tensor spec of
                the input. If nested, then ``preprocessing_combiner`` must not be
                None.
            conv_layer_params (tuple[tuple]): a tuple of tuples where each
                tuple takes a format 
                ``(filters, kernel_size, strides, padding, pooling_kernel)``,
                where ``padding`` and ``pooling_kernel`` are optional.
            fc_layer_params (tuple[int]): a tuple of integers
                representing FC layer sizes.
            activation (nn.functional): activation used for all the layers but
                the last layer.
            last_layer_size (int): an optional size of an additional layer
                appended at the very end. Note that if ``last_activation`` is
                specified, ``last_layer_size`` has to be specified explicitly.
            last_activation (nn.functional): activation function of the
                additional layer specified by ``last_layer_size``. Note that if
                ``last_layer_size`` is not None, ``last_activation`` has to be
                specified explicitly.

            Args for the generator
            ====================================================================
            noise_dim (int): dimension of noise
            noise_type (str): distribution type of noise input to the generator, 
                types are [``uniform``, ``normal``, ``categorical``, ``softmax``] 
            hidden_layers (tuple): size of hidden layers.
            use_fc_bn (bool): whether use batnch normalization for fc layers.
            particles (int): number of sampling particles
            entropy_regularization (float): weight of entropy regularization
            kernel_sharpness (float): Used only for entropy_regularization > 0.
                We calcualte the kernel in SVGD as:
                    :math:`\exp(-kernel_sharpness * reduce_mean(\frac{(x-y)^2}{width}))`
                where width is the elementwise moving average of :math:`(x-y)^2`

            Args for training
            ====================================================================
            loss_func (Callable): loss_func(outputs, targets)   
            optimizer (torch.optim.Optimizer): The optimizer for training.
            regenerate_for_each_batch (bool): If True, particles will be regenerated 
                for every training batch.
            name (str):
        """
        param_net = ParamNetwork(
            input_tensor_spec=input_tensor_spec,
            conv_layer_params=conv_layer_params,
            fc_layer_params=fc_layer_params,
            activation=activation,
            last_layer_size=last_layer_size,
            last_activation=last_activation)

        print(param_net)

        gen_output_dim = param_net.param_length
        noise_spec = TensorSpec(shape=(noise_dim, ))
        net = EncodingNetwork(
            noise_spec,
            fc_layer_params=hidden_layers,
            use_fc_bn=use_fc_bn,
            last_layer_size=gen_output_dim,
            last_activation=math_ops.identity,
            name="Generator")

        print(net)

        super().__init__(
            gen_output_dim,
            noise_dim=noise_dim,
            net=net,
            entropy_regularization=entropy_regularization,
            kernel_sharpness=kernel_sharpness,
            optimizer=optimizer,
            name=name)

        self._param_net = param_net
        self._particles = particles
        self._train_loader = None
        self._test_loader = None
        self._regenerate_for_each_batch = regenerate_for_each_batch
        self._loss_func = loss_func
        if self._loss_func is None:
            self._loss_func = F.cross_entropy
        # self._noise_sampler = NoiseSampler(
        #     noise_type, noise_dim, particles=particles)

    def set_data_loader(self, train_loader, test_loader=None):
        self._train_loader = train_loader
        self._test_loader = test_loader

    def set_particles(self, particles):
        self._particles = particles

    @property
    def particles(self):
        return self._particles

    def sample_parameters(self, particles=None):
        if particles is None:
            particles = self.particles
        params, _ = self._predict(inputs=None, batch_size=particles)
        return params

    def train_iter(self, particles=None, state=None):
        """Perform one epoch (iteration) of training."""

        assert self._train_loader is not None, "Must set data_loader first."
        if particles is None:
            particles = self.particles
        with record_time("time/train"):
            avg_acc = []
            loss = 0.
            for batch_idx, (data, target) in enumerate(
                    tqdm(self._train_loader)):
                data = data.to(alf.get_default_device())
                target = target.to(alf.get_default_device())
                if not self._regenerate_for_each_batch:
                    params = self.sample_parameters(particles=particles)
                    self._param_net.set_parameters(params)
                alg_step = self.train_step((data, target),
                                           particles=particles,
                                           state=state)
                self.update_with_gradient(alg_step.info)
                avg_acc.append(alg_step.info.extra.avg_acc)
                loss += alg_step.info.extra.loss
        acc = torch.as_tensor(avg_acc)
        logging.info("Avg acc: {}".format(acc.mean() * 100))
        logging.info("Cum loss: {}".format(loss))

        return batch_idx + 1

    def train_step(self, inputs, loss_func=None, particles=None, state=None):
        """Perform one batch of training computation.

        Args:
            inputs (nested Tensor): if None, the outputs is generated only from
                noise.
            loss_func (Callable): loss_func([outputs, inputs])
                (loss_func(outputs) if inputs is None) returns a Tensor with
                shape [batch_size] as a loss for optimizing the generator
            batch_size (int): batch_size. Must be provided if inputs is None.
                Its is ignored if inputs is not None
            state: not used

        Returns:
            AlgorithmStep:
                outputs: Tensor with shape (batch_size, dim)
                info: LossInfo
        """
        if particles is None:
            particles = self.particles
        if self._regenerate_for_each_batch:
            params = self.sample_parameters(particles=particles)
            self._param_net.set_parameters(params)
        if loss_func is None:
            loss_func = self._loss_func
        train_info, grad = self._grad_func(inputs, params, loss_func)
        loss_propagated = torch.sum(grad.detach() * params, dim=-1)

        return AlgStep(
            output=params,
            state=(),
            info=LossInfo(loss=loss_propagated, extra=train_info))

    def _stein_grad(self, inputs, outputs, loss_func):
        data, target = inputs
        logit, _ = self._param_net(data)  # [B, N, D]
        pred = logit.max(-1)[1]
        target = target.unsqueeze(1).expand(*target.shape, self.particles)
        acc = pred.eq(target).float().mean(0)
        avg_acc = acc.mean()
        loss = loss_func(logit.transpose(1, 2), target)
        loss_grad = torch.autograd.grad(loss.sum(), outputs)[0]
        logq_grad = self._score_func(outputs)

        train_info = HyperNetworkLossInfo(loss=loss, acc=acc, avg_acc=avg_acc)

        return train_info, loss_grad + logq_grad

    def _score_func(self, x, alpha=1e-3):
        r"""Compute the stein estimator of the score function 
            :math:`\nabla\log q = -(K + \alpha I)^{-1}\nabla K`

        Args:
            x (Tensor): set of N particles, shape (N x D), where D is the 
                dimenseion of each particle
            alpha (float): weight of regularization for inverse kernel

        Returns:
            :math:`\nabla\log q` (Tensor): the score function of shape (N x D)
            
        """
        N, D = x.shape
        h = self._kernel_width()

        diff = x.unsqueeze(1) - x.unsqueeze(0)  # [N, N, D]
        dist_sq = torch.sum(diff**2, -1)  # [N, N]

        kappa = torch.exp(-dist_sq / h)  # [N, N]
        kappa_inv = torch.inverse(kappa + alpha * torch.eye(N))  # [N, N]
        kappa_grad = torch.einsum('ij,ijk->jk', kappa, -2 * diff / h)  # [N, D]

        return kappa_inv @ kappa_grad

    def _kernel_width(self):
        # TODO: implement the kernel bandwidth selection via Heat equation.
        return self._kernel_sharpness

    def evaluate(self, loss_func=None):
        """Evaluate on a randomly drawn network. """

        assert self._test_loader is not None, "Must set test_loader first."
        if loss_func is None:
            loss_func = self._loss_func
        # self._net.eval()
        params = self.sample_parameters(particles=1)
        # self._net.train()
        self._param_net.set_parameters(params)
        with record_time("time/test"):
            test_acc = 0.
            test_loss = 0.
            for i, (data, target) in enumerate(self._test_loader):
                data = data.to(alf.get_default_device())
                target = target.to(alf.get_default_device())
                logit, _ = self._param_net(data)  # [B, 1, D]
                pred = logit.max(-1)[1]
                correct = pred.eq(target.view_as(pred)).long().sum()
                loss = loss_func(logit, target)
                test_acc += correct.item()
                test_loss += loss.item()

        test_acc /= len(self._test_loader.dataset)
        logging.info("Test acc: {}".format(test_acc * 100))
        logging.info("Test loss: {}".format(test_loss))
