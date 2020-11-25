import os

env_list = [
    "alien:AlienNoFrameskip-v4",
"amidar:AmidarNoFrameskip-v4",
"assault:AssaultNoFrameskip-v4",
"asterix:AsterixNoFrameskip-v4",
"asteroids:AsteroidsNoFrameskip-v4",
"atlantis:AtlantisNoFrameskip-v4",
"bank_heist:BankHeistNoFrameskip-v4",
"battle_zone:BattleZoneNoFrameskip-v4",
"beam_rider:BeamRiderNoFrameskip-v4",
"berzerk:BerzerkNoFrameskip-v4",
"bowling:BowlingNoFrameskip-v4",
"boxing:BoxingNoFrameskip-v4",
"breakout:BreakoutNoFrameskip-v4",
"centipede:CentipedeNoFrameskip-v4",
"chopper_command:ChopperCommandNoFrameskip-v4",
"crazy_climber:CrazyClimberNoFrameskip-v4",
"defender:DefenderNoFrameskip-v4",
"demon_attack:DemonAttackNoFrameskip-v4",
"double_dunk:DoubleDunkNoFrameskip-v4",
"enduro:EnduroNoFrameskip-v4",
"fishing_derby:FishingDerbyNoFrameskip-v4",
"freeway:FreewayNoFrameskip-v4",
"frostbite:FrostbiteNoFrameskip-v4",
"gopher:GopherNoFrameskip-v4",
"gravitar:GravitarNoFrameskip-v4",
"hero:HeroNoFrameskip-v4",
"ice_hockey:IceHockeyNoFrameskip-v4",
"jamesbond:JamesbondNoFrameskip-v4",
"kangaroo:KangarooNoFrameskip-v4",
"krull:KrullNoFrameskip-v4",
"kung_fu_master:KungFuMasterNoFrameskip-v4",
"montezuma_revenge:MontezumaRevengeNoFrameskip-v4",
"ms_pacman:MsPacmanNoFrameskip-v4",
"name_this_game:NameThisGameNoFrameskip-v4",
"phoenix:PhoenixNoFrameskip-v4",
"pitfall:PitfallNoFrameskip-v4",
"pong:PongNoFrameskip-v4",
"private_eye:PrivateEyeNoFrameskip-v4",
"qbert:QbertNoFrameskip-v4",
"riverraid:RiverraidNoFrameskip-v4",
"road_runner:RoadRunnerNoFrameskip-v4",
"robotank:RobotankNoFrameskip-v4",
"seaquest:SeaquestNoFrameskip-v4",
"skiing:SkiingNoFrameskip-v4",
"solaris:SolarisNoFrameskip-v4",
"space_invaders:SpaceInvadersNoFrameskip-v4",
"star_gunner:StarGunnerNoFrameskip-v4",
"tennis:TennisNoFrameskip-v4",
"time_pilot:TimePilotNoFrameskip-v4",
"tutankham:TutankhamNoFrameskip-v4",
"up_n_down:UpNDownNoFrameskip-v4",
"venture:AdventureNoFrameskip-v4",
"video_pinball:VideoPinballNoFrameskip-v4",
"wizard_of_wor:WizardOfWorNoFrameskip-v4",
"yars_revenge:YarsRevengeNoFrameskip-v4",
"zaxxon:ZaxxonNoFrameskip-v4"
]

algo_list = [
    "ac"
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
        
        