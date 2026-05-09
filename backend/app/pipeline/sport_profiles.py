"""每种运动的"画像"：高光识别 prompts + 文案语料字典。

设计原则：
- highlight_prompts：CLIP 用，描述这个运动里"值得反复回看"的瞬间。
  来自运动博主/剪辑社区对该运动"看点"的共识，比如滑雪是 carving / 喷雪 /
  起跳腾空 / 落地、攀岩是动态过点 / 顶部 / 坠落、篮球是投篮起跳 / 突破。
- boring_prompts：负向参考，分数会被减去；典型"挂机"画面（站着、走路、空场）。
- vocab.actions / sensations / gear / venues：写文案时给 LLM 当素材池，
  避免"加油热爱坚持"这种通用废话。

只对常见 14 项运动做精细 profile，其他用 GENERIC_DEFAULT 兜底。
"""
from __future__ import annotations

from typing import Dict, List, TypedDict


class SportProfile(TypedDict):
    highlight_prompts: List[str]
    boring_prompts: List[str]
    actions: List[str]
    sensations: List[str]
    gear: List[str]
    venues: List[str]
    hashtags: List[str]


PROFILES: Dict[str, SportProfile] = {
    # ---------------- 雪上 ----------------
    "双板滑雪": {
        "highlight_prompts": [
            "a skier carving a sharp turn with snow spray flying off the edges",
            "a skier launching off a kicker into the air",
            "a skier landing a jump cleanly on snow",
            "a skier blasting through deep powder with a face shot",
            "a skier weaving through trees at high speed",
            "a wipeout / fall on a snowy slope",
        ],
        "boring_prompts": [
            "a skier standing still on flat snow",
            "a person walking with skis under their arm",
            "an empty chairlift or empty groomed slope",
        ],
        "actions": [
            "立刃切弯", "压住雪刀杀回去", "起跳腾空", "落地稳压",
            "深雪打浪", "刷刀刷下来", "carving 一刀切到底", "tree run 钻林子",
        ],
        "sensations": [
            "雪刃啃住雪面那一下的回弹", "脚下蹬出去的瞬间", "雪粉糊一脸的爽",
            "呼吸跟着节奏一收一放", "重心咬住板头的咬合感", "心跳被山风拉得很慢",
        ],
        "gear": ["雪板", "雪杖", "护目镜", "头盔", "硬靴", "脱卡"],
        "venues": ["雪场", "山顶", "黑道", "powder day", "single black", "野雪线"],
        "hashtags": ["#滑雪日记", "#powderday", "#carving", "#雪季打开", "#滑雪vlog"],
    },
    "单板滑雪": {
        "highlight_prompts": [
            "a snowboarder carving a deep heelside or toeside turn with snow spray",
            "a snowboarder launching off a jump and grabbing the board mid-air",
            "a snowboarder landing a trick on a snowy slope",
            "a snowboarder riding through deep powder snow",
            "a snowboarder hitting a rail or box in a terrain park",
            "a snowboarder wiping out / falling",
        ],
        "boring_prompts": [
            "a snowboarder strapping in on flat snow",
            "an empty terrain park",
            "a person walking in snow boots without a board",
        ],
        "actions": [
            "heelside 拉一刀", "toeside 压到底", "ollie 起跳", "grab 抓板",
            "180 / 360 旋转", "落地咬住", "在 box 上 50-50", "推粉雪",
        ],
        "sensations": [
            "板底咬住雪面的拉扯感", "起跳那下从胃里抬起来的失重",
            "雪粒打在脸罩上的细碎", "膝盖压到极致再弹回来", "落地稳住时的脚踝那股劲",
        ],
        "gear": ["单板", "固定器", "雪鞋", "头盔", "护臀", "护腕"],
        "venues": ["公园", "野雪", "halfpipe", "groomer", "兔子坡"],
        "hashtags": ["#单板", "#snowboarding", "#雪季", "#公园日常", "#carving"],
    },

    # ---------------- 攀岩 ----------------
    "攀岩": {
        "highlight_prompts": [
            "a climber making a long dynamic move / dyno reaching for a hold",
            "a climber on a steep overhang clipping a quickdraw",
            "a climber matching feet on a tiny crimp under tension",
            "a climber topping out at the summit, both hands on the final hold",
            "a climber falling and being caught by the rope",
            "a climber chalking up before a hard move",
        ],
        "boring_prompts": [
            "a climber resting on the ground, putting on shoes",
            "an empty climbing wall with no climber",
            "people standing around at the base of a wall",
        ],
        "actions": [
            "dyno 飞一把", "lock off 锁死", "脚换点", "跪举 / drop knee",
            "顶端伸长 last move", "flag 挂腿稳住", "send 一发完攀",
        ],
        "sensations": [
            "前臂泵到爆", "指尖在小点上抠住的火辣", "脚踩稳那一下信任",
            "呼吸压到最深一口", "顶上抓住 jug 时那口气泄出来",
        ],
        "gear": ["岩鞋", "粉袋", "快挂", "保护器", "安全带", "镁粉"],
        "venues": ["岩馆", "天然岩壁", "preak", "外岩", "boulder area"],
        "hashtags": ["#攀岩", "#climbing", "#外岩", "#项目日记", "#send"],
    },
    "抱石": {
        "highlight_prompts": [
            "a boulderer making a dynamic jump between holds in an indoor gym",
            "a boulderer holding a tense lock-off position on colored holds",
            "a boulderer topping out a boulder problem with both hands on top",
            "a boulderer falling onto crash pads",
            "a boulderer pressing into a heel hook on an overhang",
        ],
        "boring_prompts": [
            "a person sitting on crash pads chatting",
            "an empty bouldering wall",
            "people watching at the bottom",
        ],
        "actions": [
            "dyno 飞点", "heel hook 挂跟", "toe hook 钩脚",
            "compression 抱住", "send 一发完成", "顶上稳住 mantle",
        ],
        "sensations": [
            "握把那一下指头骨节嘎嘣响", "重心拉过去的瞬间手心冒汗",
            "脚跟咬住点的踏实", "顶上一掌按下去全身松开",
        ],
        "gear": ["岩鞋", "粉袋", "刷子", "crash pad"],
        "venues": ["岩馆", "boulder area", "外岩 boulder"],
        "hashtags": ["#抱石", "#bouldering", "#岩馆日常", "#v几", "#send"],
    },

    # ---------------- 球类 ----------------
    "篮球": {
        "highlight_prompts": [
            "a basketball player jumping up to dunk the ball through the hoop",
            "a basketball player shooting a three pointer with proper form",
            "a basketball player driving past a defender to the basket",
            "a basketball player making a behind the back or crossover dribble",
            "a basketball player blocking a shot at the rim",
            "a basketball going through the net (made shot)",
        ],
        "boring_prompts": [
            "players standing during a timeout",
            "an empty basketball court",
            "players walking back on defense",
        ],
        "actions": [
            "急停跳投", "胯下变向", "突破上篮", "三分出手", "盖帽",
            "底角空位", "拉杆", "反手挑篮", "扣篮", "spot up 接球就投",
        ],
        "sensations": [
            "球出手那一下手指拨过球网的感觉", "起跳到顶点的悬停",
            "防守人贴上来呼吸压在背后", "队友传过来那一下手心的稳",
            "投完直接转身不看的自信",
        ],
        "gear": ["篮球", "护膝", "球鞋", "护臂"],
        "venues": ["球场", "野球场", "室内场", "校园篮球场"],
        "hashtags": ["#篮球日记", "#streetball", "#野球场", "#今日训练", "#hoops"],
    },
    "足球": {
        "highlight_prompts": [
            "a soccer player striking the ball with power towards the goal",
            "a soccer player dribbling past a defender",
            "a goalkeeper diving to make a save",
            "a soccer ball going into the net (goal)",
            "a header attempt during a soccer match",
        ],
        "boring_prompts": [
            "players walking on the pitch during a stoppage",
            "an empty soccer field",
            "players standing in formation",
        ],
        "actions": ["射门", "过人", "传中", "鱼跃头球", "扑救", "倒钩", "弧线球"],
        "sensations": ["脚弓内侧吃住球的厚实感", "皮球擦过草皮的摩擦",
                        "门将扑出那一秒呼吸停掉", "进球后队友撞上来的冲击"],
        "gear": ["足球", "球鞋", "护腿板"],
        "venues": ["球场", "草皮场", "室内五人制"],
        "hashtags": ["#足球", "#soccer", "#周末野球", "#进球时刻"],
    },
    "网球": {
        "highlight_prompts": [
            "a tennis player hitting a powerful forehand winner",
            "a tennis player serving aggressively",
            "a tennis player diving to reach a difficult shot",
            "a tennis ball just clipping the line",
        ],
        "boring_prompts": [
            "a player picking up a ball between points",
            "an empty tennis court",
        ],
        "actions": ["正手抽击", "反手切球", "上旋发球", "网前截击", "底线对抽"],
        "sensations": ["拍弦吃住球的弹性", "脚步交叉换位的节奏",
                        "球擦边线那一下心里咯噔"],
        "gear": ["球拍", "网球", "球鞋"],
        "venues": ["硬地", "红土场", "室内网球场"],
        "hashtags": ["#网球", "#tennis", "#周末打球", "#tennislife"],
    },

    # ---------------- 跑动类 ----------------
    "跑步": {
        "highlight_prompts": [
            "a runner crossing a finish line with arms up",
            "a runner sprinting at full speed on a track",
            "a runner running uphill with effort visible",
            "a close up of running shoes hitting the ground",
        ],
        "boring_prompts": [
            "a person standing still in running clothes",
            "an empty running path",
            "a person stretching",
        ],
        "actions": ["冲刺", "配速咬住", "上坡发力", "下坡放开", "压步频"],
        "sensations": ["呼吸顶到胸口那一下", "鞋底回弹打在心率上",
                        "汗顺着鬓角划下来", "心跳和耳机鼓点合拍"],
        "gear": ["跑鞋", "运动表", "心率带"],
        "venues": ["公园跑道", "操场", "城市路跑", "山野"],
        "hashtags": ["#跑步打卡", "#PB", "#running", "#晨跑"],
    },
    "马拉松": {
        "highlight_prompts": [
            "a marathon finish line with runners crossing",
            "a runner overtaking other runners on a city street",
            "many marathon runners packed on a road",
            "spectators cheering for marathon runners",
        ],
        "boring_prompts": [
            "an empty marathon route",
            "runners standing at a water station drinking",
        ],
        "actions": ["破三", "撞墙后再启动", "冲线", "过水站不停", "跟住兔子"],
        "sensations": ["35K 之后腿不是自己的", "终点拱门进视线那一下心一紧",
                        "完赛奖牌挂上脖子的重量"],
        "gear": ["号码布", "能量胶", "压缩袜", "心率表"],
        "venues": ["马拉松路线", "终点拱门", "起点广场"],
        "hashtags": ["#马拉松", "#完赛", "#PB", "#跑马日记"],
    },
    "骑行": {
        "highlight_prompts": [
            "a cyclist going downhill at high speed",
            "a cyclist climbing a steep mountain road, out of the saddle",
            "a peloton of cyclists riding close together",
            "a mountain biker jumping off a small drop",
        ],
        "boring_prompts": [
            "a cyclist standing next to a parked bicycle",
            "an empty road with no cyclists",
        ],
        "actions": ["摇车上坡", "下坡贴肚皮", "巡航发力", "出弯加速"],
        "sensations": ["大腿乳酸涨到极限再翻过去那一下",
                        "下坡风灌进车衣的鼓胀", "顶上回望路盘旋的成就感"],
        "gear": ["公路车", "山地车", "头盔", "码表", "锁鞋"],
        "venues": ["山路", "公路", "林道", "城市绿道"],
        "hashtags": ["#骑行日常", "#cycling", "#爬坡王", "#山地车"],
    },

    # ---------------- 水上/极限 ----------------
    "冲浪": {
        "highlight_prompts": [
            "a surfer riding inside the barrel of a wave",
            "a surfer carving a top turn with spray",
            "a surfer dropping into a steep wave",
            "a surfer wiping out in white water",
        ],
        "boring_prompts": ["a surfer paddling on a flat ocean", "an empty beach"],
        "actions": ["take off", "顶端切回 cutback", "管浪", "底部转向 bottom turn"],
        "sensations": ["浪墙立起来那一下板头压下去", "盐水钻进鼻腔",
                        "管浪里光线被吞掉的几秒"],
        "gear": ["冲浪板", "浪绳", "水鞋", "防寒衣"],
        "venues": ["海边", "万宁", "浪点", "礁盘"],
        "hashtags": ["#冲浪", "#surfing", "#万宁日常", "#海边"],
    },
    "滑板": {
        "highlight_prompts": [
            "a skateboarder doing a kickflip on the ground",
            "a skateboarder grinding on a rail or ledge",
            "a skateboarder dropping into a bowl or ramp",
            "a skateboarder bailing / falling off the board",
        ],
        "boring_prompts": ["a skateboarder pushing along a flat road",
                           "an empty skate park"],
        "actions": ["ollie", "kickflip", "grind", "manual", "drop in"],
        "sensations": ["板尾踩下去那一下", "滑过铁杆的金属嗡嗡声",
                        "落地砖头吃住轮子的踏实"],
        "gear": ["滑板", "护腕", "板鞋", "护膝"],
        "venues": ["滑板场", "街头", "bowl", "ledge"],
        "hashtags": ["#滑板", "#skateboarding", "#街头", "#trick"],
    },
    "瑜伽": {
        "highlight_prompts": [
            "a person holding a difficult yoga pose like crow or handstand",
            "a person flowing through sun salutation",
            "a person in a deep backbend on a yoga mat",
        ],
        "boring_prompts": ["a person rolling up a yoga mat", "an empty yoga studio"],
        "actions": ["乌鸦式", "下犬", "战士二", "鸽王", "倒立"],
        "sensations": ["呼吸放到丹田那一下身体松开",
                        "肩胛打开后背发烫", "倒立时血液倒流的清醒"],
        "gear": ["瑜伽垫", "瑜伽砖", "瑜伽轮", "伸展带"],
        "venues": ["瑜伽馆", "客厅", "户外草坪"],
        "hashtags": ["#瑜伽日常", "#yoga", "#呼吸", "#身心"],
    },
    "拳击": {
        "highlight_prompts": [
            "a boxer landing a clean cross or hook on a heavy bag or opponent",
            "a boxer slipping a punch and countering",
            "two boxers in a clinch in the ring",
            "a knockdown in a boxing match",
        ],
        "boring_prompts": ["a boxer wrapping their hands", "an empty boxing ring"],
        "actions": ["直拳", "勾拳", "刺拳-直拳-勾拳 1-2-3 组合", "闪躲反击", "贴身缠斗"],
        "sensations": ["手套打在沙袋上的回声",
                        "汗珠甩出去的弧线", "对手呼吸打在脖子上的热度"],
        "gear": ["拳套", "护齿", "绷带", "沙袋"],
        "venues": ["拳馆", "擂台", "搏击俱乐部"],
        "hashtags": ["#拳击", "#boxing", "#拳馆日常", "#格斗"],
    },
}


GENERIC_DEFAULT: SportProfile = {
    "highlight_prompts": [
        "an exciting and dynamic action moment in sports",
        "a person doing an impressive athletic move at high speed",
        "a moment of effort and intensity during physical activity",
        "a person mid-air or in motion during a sport",
    ],
    "boring_prompts": [
        "a person standing still doing nothing",
        "an empty scene without any action",
        "a person walking calmly",
    ],
    "actions": ["发力", "腾空", "完成动作", "全力冲刺", "落地稳住"],
    "sensations": [
        "心跳直接顶到嗓子眼", "肌肉记得每一下",
        "汗顺着脖子滑下来", "脑子里只剩这一刻", "呼吸被节奏拉长",
    ],
    "gear": ["装备"],
    "venues": ["训练场地"],
    "hashtags": ["#运动日常", "#热爱", "#一起练"],
}


def get_profile(sport: str) -> SportProfile:
    """按运动名取 profile；找不到则返回通用兜底。"""
    return PROFILES.get(sport, GENERIC_DEFAULT)
