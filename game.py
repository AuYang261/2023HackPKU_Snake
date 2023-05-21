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
        self.state = 'wait'
        self.state_lock = Lock()
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
        elif action == (self.direct + 2) % 4:
            # backward
            return
        else:
            self.direct = action

        # forward direction is the positive of the x-axis in body coordinate,
        # which means self.direct is
        # the included angle of the forward direction and the x-axis in map coordinate(in 90 degrees units)
        next_head_pos = self.bodies[0] + self.__rotate90(np.array([1, 0]), self.direct)

        if not self.__in_range(next_head_pos):
            # out of range
            self.state = 'end'
            return

        # calling the occupied callback function
        self.points[next_head_pos[0]][next_head_pos[1]].occupied_callback(self)

    def get_state(self) -> str:
        return self.state

    def get_score(self) -> int:
        return self.score


class Game:

    def __init__(self, rows, cols, speed, user_input):
        self.rows = rows
        self.cols = cols
        self.board = Board(rows, cols)
        self.speed = speed

        pygame.init()
        self.window_size = (600, 600)
        self.__screen = pygame.display.set_mode(self.window_size, 0, 32)
        pygame.display.set_caption('Snake')
        self.user_input = user_input
        self.prompt = "卡通游戏风格的" + self.user_input

        self.background_img = None

        self.block_size = (self.window_size[0] / self.cols, self.window_size[1] / self.rows)
        self.__ui_white = pygame.Surface(self.block_size)
        self.myfont = pygame.font.Font(None, 60)
        self.chat_period = 20  # s
        self.chat_last_time = -self.chat_period
        self.chat_str = ""
        self.chat_str_lock = Lock()

    def draw(self):
        if not self.__screen:
            return
        self.__screen.fill(color='white')
        self.board.state_lock.acquire()
        state = self.board.get_state()
        self.board.state_lock.release()
        if state == 'run':
            if not self.background_img:
                self.background_img = pygame.image.load('img/' + self.user_input + '.jpg').convert_alpha()
                self.background_img.set_alpha(150)
                self.background_img = pygame.transform.scale(self.background_img, self.window_size)
            self.__screen.blit(self.background_img, (0, 0))
            self.__ui_white.fill(color='red')
            self.__screen.blit(self.__ui_white,
                               (self.board.food_pos[1] * self.block_size[0], self.board.food_pos[0] * self.block_size[1]))
            for i, block in enumerate(self.board.bodies):
                if i == 0:
                    self.__ui_white.fill(color='yellow')
                else:
                    self.__ui_white.fill(color='blue')
                self.__screen.blit(self.__ui_white,
                                   (block[1] * self.block_size[0], block[0] * self.block_size[1]))
            score_text = self.myfont.render('Score: {}'.format(self.board.score), True, (0, 0, 0))
            self.__screen.blit(score_text, (0, 0))
        elif state == 'wait':
            loading_text = self.myfont.render('Loading scene...', True, (255, 0, 0))
            textRect = loading_text.get_rect()
            textRect.center = [i // 2 for i in self.window_size]
            self.__screen.blit(loading_text, textRect)
        elif state == 'end':
            if self.background_img:
                self.__screen.blit(self.background_img, (0, 0))
            end_text = self.myfont.render('Your score is {}'.format(self.board.score), True, (255, 0, 0))
            textRect = end_text.get_rect()
            textRect.center = [i // 2 for i in self.window_size]
            self.__screen.blit(end_text, textRect)

        self.__draw_chat()
        pygame.display.update()

    def __draw_chat(self):
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
        textRect.center = (self.window_size[0]/2, 0)
        textRect.bottom = self.window_size[1]
        self.__screen.blit(text, textRect)

    def get_chat_str(self):
        while True:
            state = ''
            if self.board.get_state() == 'wait':
                state = "，正在等待开始"
            elif self.board.get_state() == 'end':
                state = "，游戏已经结束"
            string = openai.aichat(
                "假设你是贪吃蛇游戏中的贪吃蛇，在{}主题下{}，你的内心想法是怎样的，用幽默的语气回答，10到20个字"
                    .format(state, self.user_input)
            ).replace('"', '').replace('“', '').replace('”', '')
            self.chat_str_lock.acquire()
            self.chat_str = string
            self.chat_str_lock.release()
            print(self.chat_str)
            time.sleep(self.chat_period)

    def get_background_img(self, prompt, size, name):
        openai.aiimg(prompt, size, name)
        self.board.state_lock.acquire()
        self.board.state = 'run'
        self.chat_str = ''
        self.board.state_lock.release()

    def restart(self):
        self.board = Board(self.rows, self.cols)

    def __del__(self):
        pygame.quit()


if __name__ == '__main__':
    user_input = input("输入场景：")
    game = Game(50, 50, random.randint(5, 20), user_input)

    threads = []
    t = Thread(target=Game.get_chat_str, args=(game,))
    t.start()
    threads.append(t)
    t = Thread(target=Game.get_background_img, args=(game, game.prompt, '512x512', game.user_input))
    t.start()
    threads.append(t)

    game.draw()
    while True:
        # print(game.board.points)
        action = -1
        for event in pygame.event.get():
            # print(event)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_s:
                    action = 0
                elif event.key == pygame.K_a:
                    action = 1
                elif event.key == pygame.K_w:
                    action = 2
                elif event.key == pygame.K_d:
                    action = 3
                elif event.key == pygame.K_ESCAPE:
                    game.board.state = 'end'
                    # pygame.quit()
                    break
        if game.board.get_state() == 'run':
            if action != -1:
                game.board.one_step(action, False)
            else:
                # forward
                game.board.one_step(1, True)
        game.draw()
        time.sleep(1 / game.speed)
    print(game.board.score)

    for t in threads:
        t.join()
