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

import gin
import torch
import torch.nn.functional as F
from typing import Callable

import alf
from alf.data_structures import AlgStep, LossInfo
from alf.algorithms.generator import Generator
from alf.algorithms.hypernetwork_networks import ParamNetwork
from alf.networks import EncodingNetwork
from alf.tensor_specs import TensorSpec
from alf.utils import common, math_ops
from alf.utils.summary_utils import record_time


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
            particles=32,
            entropy_regularization=1.,
            kernel_sharpness=2.,
            train_loader=None,
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
                tuple takes a format ``(filters, kernel_size, strides, padding)``,
                where ``padding`` is optional.
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
            particles (int): number of sampling particles
            entropy_regularization (float): weight of entropy regularization
            kernel_sharpness (float): Used only for entropy_regularization > 0.
                We calcualte the kernel in SVGD as:
                    :math:`\exp(-kernel_sharpness * reduce_mean(\frac{(x-y)^2}{width}))`
                where width is the elementwise moving average of :math:`(x-y)^2`

            Args for training
            ====================================================================
            train_loader (torch.utils.data.Dataloader): dataloader for training.
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

        gen_output_dim = param_net.param_length
        noise_spec = TensorSpec(shape=(noise_dim, ))
        net = EncodingNetwork(
            noise_spec,
            fc_layer_params=hidden_layers,
            last_layer_size=gen_output_dim,
            last_activation=math_ops.identity,
            name="Generator")

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
        self._train_loader = train_loader
        self._regenerate_for_each_batch = regenerate_for_each_batch
        self._loss_func = loss_func
        if self._loss_func is None:
            self._loss_func = F.cross_entropy
        # self._noise_sampler = NoiseSampler(
        #     noise_type, noise_dim, particles=particles)

    def set_train_loader(self, train_loader):
        self._train_loader = train_loader

    def set_particles(self, particles):
        self._particles = particles

    @property
    def particles(self):
        return self._particles

    def sample_parameters(self, particles=None):
        if particles is not None:
            self._particles = particles
        params, _ = self._predict(inputs=None, batch_size=self._particles)
        return params

    def train_iter(self, particles=None, state=None):
        """Perform one epoch (iteration) of training."""

        with record_time("time/train"):
            for batch_idx, (data, target) in enumerate(self._train_loader):
                data = data.to(alf.get_default_device())
                target = target.to(alf.get_default_device())
                if not self._regenerate_for_each_batch:
                    params = self.sample_parameters(particles=particles)
                    self._param_net.set_parameters(params)
                alg_step = self.train_step((data, target),
                                           particles=particles,
                                           state=state)
                self.update_with_gradient(alg_step.info)

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

        if self._regenerate_for_each_batch:
            params = self.sample_parameters(particles=particles)
            self._param_net.set_parameters(params)
        if loss_func is None:
            loss_func = self._loss_func
        loss, grad = self._grad_func(inputs, params, loss_func)
        loss_propagated = torch.sum(grad.detach() * params, dim=-1)

        return AlgStep(
            output=params,
            state=(),
            info=LossInfo(loss=loss_propagated, extra=loss))

    def _stein_grad(self, inputs, outputs, loss_func):
        data, target = inputs
        pred, _ = self._param_net(data)
        target = target.unsqueeze(1).expand(*target.shape, self.particles)
        loss = loss_func(pred.transpose(1, 2), target)
        loss_grad = torch.autograd.grad(loss.sum(), outputs)[0]

        logq_grad = self._score_func(outputs)

        return loss, loss_grad + logq_grad

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