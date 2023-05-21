# -*- coding = utf-8 -*-
# @Time : 2023/5/20 21:00
# @Author : AuYang
# @File : game.py
# @Software : PyCharm

import os
import time

import numpy as np
import random
import pygame
from Grid import *
import openai
from threading import Thread, Lock
import unicodedata


def is_chinese(string):
    for char in string:
        if 'CJK' in unicodedata.name(char):
            return True
    return False


class Board:
    """
    The positive of x-axis and y-axis of map coordinate is down and right
    """

    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.bodies = [np.array([rows // 2, cols // 2])]
        self.points = [[Grid(pos=np.array([j, i]), prototype=Blank()) for i in range(cols)] for j in range(rows)]
        # 0: blank, 1: head, 2: body, 3: food
        self.points[self.bodies[0][0]][self.bodies[0][1]] = Grid(pos=np.array(self.bodies[0]), prototype=Body())
        self.availables = list(range(self.rows * self.cols))
        self.availables.remove(self.xy2liner(self.bodies[0]))
        self.food_pos = self.gen_food()
        # 0: down, 1: left, 2: up, 3: right
        self.direct = 0
        # running or end
        self.running = True
        self.smell_dist = 3
        self.die_reward = -5
        self.food_reward = 2
        self.score = 0
        self.steps = 0

    def gen_food(self) -> np.array:
        liner = random.choice(self.availables)
        xy = self.liner2xy(liner)
        self.points[xy[0]][xy[1]] = Grid(pos=np.array(xy), prototype=Food1())
        return xy

    def xy2liner(self, xy: np.array or list[np.array]) -> int or list[int]:
        return xy[0] * self.cols + xy[1]

    def liner2xy(self, liner: int) -> np.array:
        return np.array([liner // self.cols, liner % self.cols])

    def __in_range(self, xy: np.array) -> bool:
        return 0 <= xy[0] < self.rows and 0 <= xy[1] < self.cols

    @staticmethod
    def __rotate90(vector: np.array, count: int) -> np.array:
        """
        rotate vector count*90 degrees clockwise
        """
        # clockwise to anticlockwise
        radian = -count * np.pi / 2
        c = round(np.cos(radian))
        s = round(np.sin(radian))
        return np.dot(vector, np.array([[c, s], [-s, c]])).astype(int)

    def one_step(self, action: int, relative: bool = True):
        """
        @return the reward
        """

        self.steps += 1
        if relative:
            if action == 1:
                # forward
                pass
            elif action == 2:
                # turn right
                self.direct = (self.direct + 1) % 4
            elif action == 3:
                # turn left
                self.direct = (self.direct - 1) % 4
            else:
                raise Exception("Unknown action {}".format(action))
        else:
            self.direct = action

        # forward direction is the positive of the x-axis in body coordinate,
        # which means self.direct is
        # the included angle of the forward direction and the x-axis in map coordinate(in 90 degrees units)
        next_head_pos = self.bodies[0] + self.__rotate90(np.array([1, 0]), self.direct)

        if not self.__in_range(next_head_pos):
            # out of range
            self.running = False
            return

        # calling the occupied callback function
        self.points[next_head_pos[0]][next_head_pos[1]].occupied_callback(self)

    def get_running(self) -> bool:
        return self.running

    def get_score(self) -> int:
        return self.score


class Game:

    def __init__(self, rows, cols, speed, display=True):
        self.rows = rows
        self.cols = cols
        self.board = Board(rows, cols)
        self.speed = speed
        self.display = display
        self.action = 0

        if self.display:
            pygame.init()
            self.window_size = (600, 600)
            self.block_size = (self.window_size[0] / self.cols, self.window_size[1] / self.rows)
            self.__screen = pygame.display.set_mode(self.window_size, 0, 32)
            pygame.display.set_caption('Snake')
            self.__ui_white = pygame.Surface(self.block_size)
            self.myfont = pygame.font.Font(None, 60)
            self.chat_period = 20  # s
            self.chat_last_time = -self.chat_period
            self.chat_str = ""
            self.chat_str_lock = Lock()

            head0 = pygame.transform.scale(pygame.image.load('pic/down.png'), self.block_size)
            head1 = pygame.transform.scale(pygame.image.load('pic/left.png'), self.block_size)
            head2 = pygame.transform.scale(pygame.image.load('pic/up.png'), self.block_size)
            head3 = pygame.transform.scale(pygame.image.load('pic/right.png'), self.block_size)
            self.heads = [head0, head1, head2, head3]
            self.body = pygame.transform.scale(pygame.image.load('pic/body.png'), self.block_size)
            self.food = pygame.transform.scale(pygame.image.load('pic/food.png'), self.block_size)

    def draw(self):
        if not self.__screen:
            return
        self.__screen.fill(color='white')
        self.__screen.blit(self.food,
                           (self.board.food_pos[1] * self.block_size[0], self.board.food_pos[0] * self.block_size[1]))
        for i, block in enumerate(self.board.bodies):
            if i == 0:
                self.__screen.blit(self.heads[self.action],
                                   (block[1] * self.block_size[0], block[0] * self.block_size[1]))
            else:
                self.__screen.blit(self.body,
                                   (block[1] * self.block_size[0], block[0] * self.block_size[1]))
        score_text = self.myfont.render('Score: {}'.format(self.board.score), True, (0, 0, 0))
        self.__screen.blit(score_text, (0, 0))
        self.__draw_chat()
        pygame.display.update()

    def __draw_chat(self):
        if self.display:
            chat = pygame.font.SysFont(random.choice([i for i in pygame.font.get_fonts() if is_chinese(i)]), 20)
            self.chat_str_lock.acquire()
            text = chat.render(
                self.chat_str,
                True,
                (0, 0, 0)
                # [random.randint(0, 255) for i in range(3)]
                # [random.randint(0, 255) for i in range(3)]
            )
            self.chat_str_lock.release()
            # 获得显示对象的 rect区域大小
            textRect = text.get_rect()
            # 设置显示对象居中
            textRect.center = (300, 200)
            self.__screen.blit(text, textRect)

    def get_chat_str(self):
        while True:
            # string = openai.aichat("假设你是贪吃蛇游戏中的贪吃蛇，你的内心想法是怎样的，用幽默的语气回答，10到20个字") \
            #     .replace('"', '')
            self.chat_str_lock.acquire()
            self.chat_str = "string"
            self.chat_str_lock.release()
            print(self.chat_str)
            time.sleep(self.chat_period)

    def restart(self):
        self.board = Board(self.rows, self.cols)

    def __del__(self):
        pygame.quit()


if __name__ == '__main__':
    game = Game(60, 60, 10, True)
    t = Thread(target=Game.get_chat_str, args=(game,))
    t.start()
    game.draw()
    while game.board.get_running():
        # print(game.board.points)
        flag = 0
        for event in pygame.event.get():
            # print(event)
            if event.type == pygame.KEYDOWN:
                flag = 1
                if event.key == pygame.K_s:
                    if game.action != 2:  # 如果当前方向不是向上
                        game.action = 0
                elif event.key == pygame.K_a:
                    if game.action != 3:  # 如果当前方向不是向右
                        game.action = 1
                elif event.key == pygame.K_w:
                    if game.action != 0:  # 如果当前方向不是向下
                        game.action = 2
                elif event.key == pygame.K_d:
                    if game.action != 1:  # 如果当前方向不是向左
                        game.action = 3
        if flag:
            game.board.one_step(game.action, False)
        else:
            # forward
            game.board.one_step(1, True)
        game.draw()
        time.sleep(1 / game.speed)
    print(game.board.score)
    t.join()
