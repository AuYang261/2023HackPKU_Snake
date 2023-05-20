# -*- coding = utf-8 -*-
# @Time : 2023/5/21 00:07
# @Author : AuYang
# @File : Grid.py
# @Software : PyCharm

import numpy as np
from abc import ABC, abstractmethod


class GridBase:
    """
    The grid baseclass
    """

    def __init__(self, pos: np.array):
        self.pos = pos
        pass


def check_board(func):
    def wrapper(*args):
        if args[2].__class__.__name__ != 'Board':
            raise Exception("The 2nd arg 'board' is not the instance of class 'Board'")

    return wrapper


class GridPrototype:
    def __init__(self):
        pass

    @abstractmethod
    @check_board
    def occupied_callback(self, grid_base: GridBase, board, *args):
        pass

    @abstractmethod
    @check_board
    def leave_callback(self, grid_base: GridBase, board, *args):
        pass


class Blank(GridPrototype):
    def __init__(self):
        super(Blank, self).__init__()

    def occupied_callback(self, grid_base: GridBase, board, *args):
        # blank
        board.availables.remove(board.xy2liner(grid_base.pos))
        board.points[grid_base.pos[0]][grid_base.pos[1]].prototype = Head()
        last = board.bodies[-1]
        if board.bodies:
            board.points[board.bodies[0][0]][board.bodies[0][1]].prototype = Body()
        else:
            board.points[board.bodies[0][0]][board.bodies[0][1]].prototype = Blank()
        board.points[last[0]][last[1]].leave_callback(board)
        board.bodies.insert(0, grid_base.pos)
        pass

    def leave_callback(self, grid_base: GridBase, board, *args):
        pass


class Head(GridPrototype):
    def __init__(self):
        super(Head, self).__init__()

    def occupied_callback(self, grid_base: GridBase, board, *args):
        # head
        raise Exception("There are two heads in ({}, {}) and ({}, {})".format(*board.bodies[0], *grid_base.pos))

    def leave_callback(self, grid_base: GridBase, board, *args):
        pass


class Body(GridPrototype):
    def __init__(self):
        super(Body, self).__init__()

    def occupied_callback(self, grid_base: GridBase, board, *args):
        # colliding body
        board.running = False

    def leave_callback(self, grid_base: GridBase, board, *args):
        board.availables.append(board.xy2liner(grid_base.pos))
        board.points[board.bodies[-1][0]][board.bodies[-1][1]].prototype = Blank()
        board.bodies.pop()


class Food1(GridPrototype):
    def __init__(self):
        super(Food1, self).__init__()

    def occupied_callback(self, grid_base: GridBase, board, *args):
        # food
        board.availables.remove(board.xy2liner(grid_base.pos))
        board.points[grid_base.pos[0]][grid_base.pos[1]].prototype = Head()
        board.points[board.bodies[0][0]][board.bodies[0][1]].prototype = Body()
        board.bodies.insert(0, grid_base.pos)
        board.food_pos = board.gen_food()
        board.score += 1

    def leave_callback(self, grid_base: GridBase, board, *args):
        raise Exception("Cannot leave food")


class Grid():
    """
    The grid baseclass
    """

    def __init__(self, pos: np.array, prototype: GridPrototype):
        self.base = GridBase(pos)
        self.prototype = prototype
        pass

    def occupied_callback(self, board, *args):
        self.prototype.occupied_callback(self.base, board, *args)

    def leave_callback(self, board, *args):
        self.prototype.leave_callback(self.base, board, *args)

