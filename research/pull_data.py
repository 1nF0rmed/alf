from gym import envs

all_envs = envs.registry.all()
env_ids = [env_spec.id for env_spec in all_envs]

def find(query):
    for i in env_ids:
        env = i.lower()
        if query in env and "noframeskip-v4" in env:
            return i
    return -1

base_names = [
    "alien",
    "amidar",
    "assault",
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

count = 0

for name in base_names:
    ret = find(''.join(name.split("_")))
    if ret==-1:
        continue
    else:
        print(name+":"+ret)
        count += 1

print("\nEnv Count: "+str(count))