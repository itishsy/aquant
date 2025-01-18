# 需要远程到游戏桌面, 远程桌面分辩设置为：1440*900
# 游戏窗口最大化，牌需要设置为4色

# 桌面信息定位
# 位置： POSITION_XXX = (x,y) 即left和top
# 区域：REGION_XXX = (x,y,w,h)
# 颜色：COLOR_XXX = (r,g,b)
# 定位：LOCATION_XXX = (position, color)


# 游戏窗口标题
WIN_TITLE = "192.168.0.113 - 远程桌面连接"
# 截图区域相对于左上角的偏移位
WIN_OFFSET = (0, 0)

SB = 0.01
BB = 0.02


# 牌
# 4种花色的颜色值。黑桃（Spade）红桃（Heart）梅花（Club）方块（Diamond）
SUIT_COLOR = ((0, 0, 0), (202, 23, 27), (29, 126, 45), (1, 30, 196))
# 单个牌要截取的宽度和高度
CARD_WIDTH, CARD_HEIGHT = 45, 55
# 第1张牌识别区域、花色位置
REGION_CARD_1 = (650, 690, CARD_WIDTH, CARD_HEIGHT)
POSITION_SUIT_1 = (676, 751)
# 第2张牌识别区域、花色位置
REGION_CARD_2 = (718, 690, CARD_WIDTH, CARD_HEIGHT)
POSITION_SUIT_2 = (737, 746)
# 第3张牌识别区域、花色位置
REGION_CARD_3 = (486, 408, CARD_WIDTH, CARD_HEIGHT)
POSITION_SUIT_3 = (546, 486)
# 公共牌之间的间隔
PUB_CARD_SPACE_X = 100

# 底池
# 底池区域（l,t,w,h)
REGION_POOL = (729, 368, 88, 30)

# 玩家
PLAYER_WIDTH, PLAYER_HEIGHT = 135, 31
REGION_PLAYER_1 = (194, 657, PLAYER_WIDTH, PLAYER_HEIGHT)
REGION_PLAYER_2 = (233, 304, PLAYER_WIDTH, PLAYER_HEIGHT)
REGION_PLAYER_3 = (666, 230, PLAYER_WIDTH, PLAYER_HEIGHT)
REGION_PLAYER_4 = (1099, 309, PLAYER_WIDTH, PLAYER_HEIGHT)
REGION_PLAYER_5 = (1137, 658, PLAYER_WIDTH, PLAYER_HEIGHT)

# 判断
# 表示需要读牌桌信息的位置及颜色值（出现手牌）
POSITION_READY = (701, 724)
COLOR_READY = (239, 239, 239)

# 牌桌识别
COLOR_TABLE = (19, 90, 22)
POSITION_TABLE = (733, 647)

# bottom所在位置
COLOR_BOTTOM = (239, 195, 44)   # D标记颜色
POSITION_BOTTOM_0 = (648, 657)  # 我
POSITION_BOTTOM_1 = (392, 634)  # 左下
POSITION_BOTTOM_2 = (392, 353)  # 左上
POSITION_BOTTOM_3 = (672, 303)  # 上
POSITION_BOTTOM_4 = (1057, 353)  # 右上
POSITION_BOTTOM_5 = (1057, 634)  # 右下

# 按钮颜色
COLOR_BUTTON = (171, 67, 63)
# 牌桌背景颜色
COLOR_TABLE_BACKGROUND = (34, 34, 34)
# 表示需要操作的位置及颜色值（出现弃牌按钮）
POSITION_BUTTON_FOLD = (937, 860)
POSITION_BUTTON_CALL = (1096, 860)
POSITION_BUTTON_RAISE = (1252, 860)

# 操作
ACTION_CHECK_POSITION = (1052, 852)
