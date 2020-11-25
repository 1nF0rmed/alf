import os

env_list = [
    "pendulum:Pendulum-v0",
    "bipedal_walker_hardcore:BipedalWalkerHardcore-v2",
    "lunar_landing:LunarLanderContinuous-v2",
    "bipedal_walker:BipedalWalker-v2",
    "mountain_car:MountainCarContinuous-v0"
]

algo_list = [
    "sac",
    "ppo",
    "ddpg",
]

curFolder = os.getcwd()
templateFolder = os.path.join(
                        os.path.join(curFolder, 'research'),
                        'templates'    
                    )

for algo in algo_list:
    algoConfigPath = os.path.join(
                        os.path.join(
                            os.path.join(curFolder, 'research'),
                            'config'),
                        algo      
                    )
    algoTemplatePath = os.path.join(templateFolder, algo+"_template.gin")
    print("Algo template path: "+algoTemplatePath)
    data = ""
    
    with open(algoTemplatePath, "r") as f:
        data = f.read()
    

    for env in env_list:
        envName, envId = env.split(":")[0], env.split(":")[1]
        print("Env path: "+os.path.join(algoConfigPath, algo+"_"+envName+".gin"))
        
        with open(os.path.join(algoConfigPath, algo+"_"+envName+".gin"), "w") as f:
            f.write(data.format(envId))
        
        