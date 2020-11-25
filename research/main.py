from termcolor import colored, cprint
from datetime import datetime
import multiprocessing
import subprocess
import random
import time
import sys
import os

def clear():
    os.system('clear')

def train(gin_file, log_dir, logPath):
    cmd = "python -m alf.bin.train --gin_file={0} --root_dir={1}".format(gin_file, log_dir)

    """
    totalTime = random.randint(20, 30)

    randCmd = random.randint(1,2)

    if randCmd==1:
        cmd = "sleep "+str(totalTime)+"s &echo hello world"
    else:
        sys.exit(-1)
    """
    

    _, ginFileName = os.path.split(gin_file)
    
    # Create the logFolder
    # Format: log_folder+config_file name
    logFile = os.path.join(logPath, ginFileName+".log")

    try:

        # Log the process output to log file
        with open(logFile, 'a') as f:
            f.write("[TIMESTAMP] "+datetime.now().strftime('%Y-%m-%d %H:%M:%S')+"\n")
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            for line in iter(process.stdout.readline, b''):
                # sys.stdout.write(line.decode(sys.stdout.encoding))
                f.write(line.decode(sys.stdout.encoding))
            if process.stderr:
                raise Exception(process.stderr)
    except Exception as e:
        with open(logFile, 'a') as f:
            f.write(str(e))

        sys.exit(-1)
    except KeyboardInterrupt:
        with open(logFile, 'a') as f:
            f.write("[LOG] Keyboard Interrupt")

        sys.exit(-1)
    
        

def main():
    # Set start method to spawn
    multiprocessing.set_start_method('spawn')

    # Defined Algorithms
    atari_envs = ["alien","amidar","assault",
    "asterix",
    "asteroids",
    "atlantis",
    "bank_heist",
    "battle_zone",
    "beam_rider",
    "berzerk",
    "bowling",
    "boxing",
    "breakout",
    "centipede",
    "chopper_command",
    "crazy_climber",
    "defender",
    "demon_attack",
    "double_dunk",
    "enduro",
    "fishing_derby",
    "freeway",
    "frostbite",
    "gopher",
    "gravitar",
    "hero",
    "ice_hockey",
    "jamesbond",
    "kangaroo",
    "krull",
    "kung_fu_master",
    "montezuma_revenge",
    "ms_pacman",
    "name_this_game",
    "phoenix",
    "pitfall",
    "pong",
    "private_eye",
    "qbert",
    "riverraid",
    "road_runner",
    "robotank",
    "seaquest",
    "skiing",
    "solaris",
    "space_invaders",
    "star_gunner",
    "tennis",
    "time_pilot",
    "tutankham",
    "up_n_down",
    "venture",
    "video_pinball",
    "wizard_of_wor",
    "yars_revenge",
    "zaxxon"
    ]
    continuous_envs = ["pendulum", "mountain_car", "bipedal_walker", "bipedal_walker_hardcore", "lunar_landing"]

    algos = {
        "ppo":continuous_envs,
        "ddpg":continuous_envs,
        "sac":continuous_envs,
        #"ac":atari_envs,
        "muzero":["go66"]
    }

    # Number of cores
    numCores = multiprocessing.cpu_count()

    print("Number of Cores: "+str(numCores))
    #return

    # Get the current folder
    curFolder = os.getcwd()

    # Path to store process running logs
    outputLogs = os.path.join(curFolder, 'logs')


    # Check if folder doesn't exists
    if not os.path.exists(outputLogs):
        # Create folder for logs
        os.mkdir(outputLogs)
    
    # Check if folder doesn't exists
    if not os.path.exists(os.path.join(curFolder, 'tensorboard')):
        # Create folder for logs
        os.mkdir(os.path.join(curFolder, 'tensorboard'))

    algoLogPath = os.path.join(curFolder, 'tensorboard')

    # Adds algo-
    for algo in algos:

        # Check if algo folder exists in tensorboard
        if not os.path.exists(os.path.join(algoLogPath, algo)):
            # Create folder
            os.mkdir(os.path.join(algoLogPath, algo))

        environments = algos[algo]

        # Adds run at end
        for run in [1,2,3]:
            # Creates algo-env-run
            for i in range(0, len(environments), numCores):

                envs = environments[i:i+numCores]

                processes = {}

                for e in envs:

                    # Check if algo-env-run folder exists in tensorboard
                    tensorboardAlgoEnvPath = os.path.join(os.path.join(os.path.join(algoLogPath, algo), e), str(run))
                    if not os.path.exists(tensorboardAlgoEnvPath):
                        # Create folder
                        os.makedirs(tensorboardAlgoEnvPath)
                    
                    # Path the algo configuration for algo-env
                    algoConfigPath = os.path.join( 
                            os.path.join(
                                os.path.join(os.path.join(curFolder, "research"), "config"),
                                algo),
                            algo+"_"+e+".gin"
                    )

                    #print(tensorboardAlgoEnvPath)
                    #return

                    p = multiprocessing.Process(target=train, args=(algoConfigPath, tensorboardAlgoEnvPath, outputLogs,))
                    processes[algo+"-"+e+"-"+str(run)] = p

                    p.start()
    
                #for process in processes:
                #    process.join()
    
                while True:
                    clear()
                    cprint("Algo: "+algo+" Run: "+str(run)+" Batch: "+str(i),  'magenta', attrs=['bold', 'underline'])
                    for process in processes:
                        print(process+": ", end='')
                        if processes[process].is_alive():
                            cprint("RUNNING", 'blue')
                        else:
                            if processes[process].exitcode==0:
                                cprint("DONE", 'green')
                            else:
                                cprint("FAILED", 'red', attrs=['blink'])
        
                    if all(not processes[process].is_alive() for process in processes):
                        #clear()
                        break
                    time.sleep(2)

    print("Training Complete! Please send us the tensorboard and logs folder")
    

if __name__ == "__main__":
    main()
