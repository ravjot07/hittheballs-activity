# -*- coding: utf-8 -*-

"""
HitTheBalls : hit the ball(s) with the good result.
Copyright (C) 2013  Laurent Bernabe <laurent.bernabe@gmail.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

"""
Manages the main game.
"""

import os

from gettext import gettext as _
from gi.repository import Gtk
import pygame
from random import randint
from sys import exit
from pygame.locals import QUIT, USEREVENT, MOUSEBUTTONUP
from elements_painter import paint_ball, paint_time_bar, paint_result_bar,\
    paint_results
from time_bar import TimeBar
from result_bar import ResultBar
from game_state import GameState
from balls_generator import BallsGenerator
import balls_collision
from operation import OPER_ADD, OPER_SUB, OPER_MUL, OPER_DIV
from balls_generator import OperationConfig

from sugar3.activity.activity import get_activity_root

class Game:

    """
    Manages the game.
    """

    def __init__(self):
        """
        Constructor.
        """
        self._initialized = False
        self.s = self.p = []
        self.powerup_manager = PowerUpManager()

    def _lazy_init(self):
        """
        Lazy initialization : main code is only called once, thanks to
        an internal flag.
        """
        if self._initialized:
            return
        pygame.init()
        self._LEFT_BUTTON = 1
        self._FPS = 10
        self._MENU_LEVELS_RECTS_Y_GAP = 30
        self._MENU_LEVELS_RECTS_WIDTH = 345
        self._MENU_LEVELS_RECTS_HEIGHT = 60
        self._MENU_LEVELS_RECTS_TXT_OFFSET = (60, -2)
        self._MENU_LEVELS_RECTS_BG_COLOR = (255, 0, 0)
        self._MENU_LEVELS_RECTS_TXT_COLOR = (255, 255, 0)
        self._MENU_BACKGROUND = (255, 255, 255)
        self._GAME_BACKGROUND = (255, 255, 255)
        self._TIME_BAR_HEIGHT = 20
        self._BLACK = (0, 0, 0)
        self._BLUE = (0, 0, 255)
        self._YELLOW = (255, 255, 0)
        self._RED = (255, 0, 0)
        self._DARK_GREEN = (0, 100, 0)
        self._GRAY = (200, 200, 200)
        self.score = 0
        self.click_sound = pygame.mixer.Sound("assets/clicksound.ogg")
        self.click_sound.set_volume(0.3)
        self.correct_ans = pygame.mixer.Sound("assets/correctans.ogg")
        self.wrong_ans = pygame.mixer.Sound("assets/wrongans.ogg")
        pygame.mixer.music.load("assets/theme.ogg")
        pygame.mixer.music.play(-1)

        self._screen = pygame.display.get_surface()
        if not(self._screen):
            self._size = (600, 400)
            self._screen = pygame.display.set_mode(self._size)
            pygame.display.set_caption("Hit the balls")
        else:
            self._size = self._screen.get_size()

        self._game_font = pygame.font.Font(None, 34)
        self._menu_font = pygame.font.Font(None, 90)
        self._end_font = pygame.font.Font(None, 40)

        self._clock = pygame.time.Clock()
        self._levels = [
            # level 1
            [OperationConfig(OPER_ADD, 9, 9),
             OperationConfig(OPER_MUL, 9, 9),
             OperationConfig(OPER_SUB, 18, 9),
             OperationConfig(OPER_DIV, 81, 9, 9)],
            # level 2
            [OperationConfig(OPER_ADD, 99, 99, 100),
             OperationConfig(OPER_MUL, 99, 9),
             OperationConfig(OPER_SUB, 100, 98),
             OperationConfig(OPER_DIV, 891, 9, 99)],
            # level 3
            [OperationConfig(OPER_ADD, 999, 999, 1000),
             OperationConfig(OPER_MUL, 99, 99, 1000),
             OperationConfig(OPER_SUB, 1000, 998),
             OperationConfig(OPER_DIV, 1000, 99)]
        ]
        self._MENU_LEVELS_RECT_X = (self._size[0] -
                                    self._MENU_LEVELS_RECTS_WIDTH) / 2
        self._MENU_LEVEL_1_RECT_Y = (self._size[1] -
                                     (self._MENU_LEVELS_RECTS_HEIGHT +
                                      self._MENU_LEVELS_RECTS_Y_GAP) *
                                     len(self._levels) +
                                     self._MENU_LEVELS_RECTS_Y_GAP) / 2

        self._levels_rect = [(self._MENU_LEVELS_RECT_X,
                              self._MENU_LEVEL_1_RECT_Y +
                              y * (self._MENU_LEVELS_RECTS_HEIGHT +
                                   self._MENU_LEVELS_RECTS_Y_GAP),
                              self._MENU_LEVELS_RECTS_WIDTH,
                              self._MENU_LEVELS_RECTS_HEIGHT)
                             for y in range(len(self._levels))]
        self._initialized = True

    def _get_result_at_pos(self, point, balls_list):
        """
        Returns the result of the ball located at point (from the balls_list)
        and its index in the balls_list,
        if any, else returns None.
        point : point to test => tuple of 2 integers
        balls_list : list of balls to test => list of Ball
        => dictionnary with "result" key => value : integer
                             "index" key => value : integer
        """
        for ball_index in range(len(balls_list)):
            ball = balls_list[ball_index]
            if ball.contains(point):
                return {"result": ball.get_operation().get_result(),
                        "index": ball_index}
        return None

    def _all_target_balls_destroyed(self, target_result, balls_list):
        """
        Says whether all target ball, those with the expected result, have been
        removed from the given list.
        target_result : expected result => integer
        balls_list : list of balls => list of Ball
        => Boolean
        """
        for ball in balls_list:
            if ball.is_visible() \
                    and ball.get_operation().get_result() == target_result:
                return False
        return True

    def _point_in_rect(self, point, rect):
        """
        Says whether a point is in a rect.
        point : the point to test => tuple of 2 integers (x,y)
        rect : the rect to test => tuple of 4 integers (x,y, width, height)
        => Boolean
        """
        x_good = point[0] >= rect[0] and point[0] <= rect[0] + rect[2]
        y_good = point[1] >= rect[1] and point[1] <= rect[1] + rect[3]
        return x_good and y_good

    def _update(self):
        """
        Update the screen rectangles that have been changed by drawing
        actions since the last update (self.s), including rectangles
        that were cleared the previous update (self.p), then clear the
        current rectangles (self.s) in preparation for the next cycle.
        """
        pygame.display.update(self.s + self.p)
        self.p = self.s
        for r in self.s:
            self._screen.fill(self._GAME_BACKGROUND, r)
        self.s = []

    def _play_game(self, time_seconds, operations_config):
        """ The main game routine
            time_seconds : time limit in seconds => integer
            operations_config : configurations for the wanted operations
            => list of
            OperationConfig.
        """
        self._screen.fill(self._MENU_BACKGROUND)
        self._update()

        self.score = 0
        game_state = GameState.NORMAL

        result_bar = ResultBar(self._game_font, txt_color=self._YELLOW,
                               bg_color=self._RED,
                               header=_("Hit the ball (or the balls) with result : "),
                               width=self._size[0])
        RESULT_BAR_HEIGHT = result_bar.get_height()

        time_bar = TimeBar(self._size[0], self._TIME_BAR_HEIGHT,
                           self._DARK_GREEN,
                           self._GRAY, lftp_edge=(0, RESULT_BAR_HEIGHT))
        # Don't forget that it will take time argument * 10 milliseconds
        time_bar.start(time_seconds * 100, 1)

        balls_area = (0, self._TIME_BAR_HEIGHT + RESULT_BAR_HEIGHT,
                      self._size[0], self._size[1])

        the_balls = BallsGenerator().generate_list(5, operations_config,
                                                   balls_area, self._game_font,
                                                   self._BLACK)

        result_index = randint(1, len(the_balls)) - 1
        target_result = the_balls[result_index].get_operation().get_result()
        result_bar.set_result(target_result)

        balls_collision.place_balls(the_balls, balls_area)

        show_status = True

        while True:
            while Gtk.events_pending():
                Gtk.main_iteration()
            self._update()
            self.s += paint_result_bar(result_bar, self._screen)
            self.s += paint_time_bar(time_bar, self._screen)
            if game_state == GameState.NORMAL:
                for ball in the_balls:
                    self.s += paint_ball(ball, self._screen)

                for event in pygame.event.get():
                    if event.type == QUIT:
                        pygame.quit()
                        exit()
                    elif event.type == USEREVENT + 1:
                        time_bar.decrease()
                        if time_bar.is_empty():
                            game_state = GameState.OVER
                    elif event.type == MOUSEBUTTONUP:
                        if event.button == self._LEFT_BUTTON:
                            self.click_sound.play()
                            event_pos = event.pos
                            clicked_ball = self.\
                                _get_result_at_pos(event_pos, the_balls)
                            if clicked_ball is not None:
                                if clicked_ball["result"] == target_result:
                                    self.correct_ans.play()
                                    the_balls[clicked_ball["index"]].hide()
                                    if self.\
                                        _all_target_balls_destroyed(
                                            target_result, the_balls):
                                        self.score += 1
                                        the_balls = BallsGenerator().generate_list(5, operations_config,
                                                                                   balls_area, self._game_font,
                                                                                   self._BLACK)
                                        balls_collision.place_balls(the_balls, balls_area)
                                        target_result = the_balls[result_index].get_operation().get_result()
                                        result_bar.set_result(target_result)
                                else:
                                    self.wrong_ans.play()
                                    game_state = GameState.LOST
                for ball in the_balls:
                    ball.move()
                balls_collision.manage_colliding_balls(the_balls)
                self._clock.tick(self._FPS)
            else:
                self.s += paint_results(balls_area, the_balls, self._screen)
                # Blinks the status text.
                if show_status:
                    self.save_highscore()
                    if game_state == GameState.OVER:
                        end_txt = _("Gave over! You ran out of time")
                    else:
                        end_txt = _("Game over! You chose incorrectly")
                    end_txt_surface = self._end_font.render(end_txt, True,
                                                            self._BLACK)
                    score_txt_surface = self._end_font.render(f"Your score was {self.score}", True,
                                                              self._BLACK)
                    highscore_txt_surface = self._end_font.render(f"and Highscore is {self.load_highscore()}", True,
                                                                   self._BLACK)
                    restart_txt_surface = self._end_font.render("click anywhere to restart", True,
                                                                self._BLACK)
                    txt_pos = [int(self._size[0] / 8), int(self._size[1] / 2.6)]
                    self.s.append(self._screen.blit(end_txt_surface, txt_pos))
                    txt_pos[1] += end_txt_surface.get_rect().height + 5
                    self.s.append(self._screen.blit(score_txt_surface, txt_pos))
                    txt_pos[1] += end_txt_surface.get_rect().height + 5
                    self.s.append(self._screen.blit(highscore_txt_surface, txt_pos))
                    txt_pos[1] += end_txt_surface.get_rect().height + 25
                    self.s.append(self._screen.blit(restart_txt_surface, txt_pos))

                for event in pygame.event.get():
                    if event.type == QUIT:
                        pygame.quit()
                        exit()
                    elif event.type == MOUSEBUTTONUP:
                        if event.button == self._LEFT_BUTTON:
                            return
                self._clock.tick(5)

    def show_menu(self):
        """
        Manages the main menu.
        """
        self._lazy_init()
        self.s = []
        self.s.append(self._screen.fill(self._MENU_BACKGROUND))
        self._update()
        while True:
            while Gtk.events_pending():
                Gtk.main_iteration()
            self._update()
            for box_index in range(len(self._levels)):
                box_value = self._levels_rect[box_index]
                s = pygame.draw.rect(
                    self._screen, self._MENU_LEVELS_RECTS_BG_COLOR,
                    box_value)
                self.s.append(s)
                txt = _("Level ") + str(box_index + 1)
                txt_surface = self._menu_font.render(txt, True,
                                                     self._MENU_LEVELS_RECTS_TXT_COLOR)
                s = self._screen.blit(txt_surface,
                                  (self._levels_rect[box_index][0] +
                                   self._MENU_LEVELS_RECTS_TXT_OFFSET[0],
                                   self._levels_rect[box_index][1] +
                                   self._MENU_LEVELS_RECTS_TXT_OFFSET[1]
                                   ))
                self.s.append(s)

            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    exit()
                if event.type == MOUSEBUTTONUP:
                    if event.button == self._LEFT_BUTTON:
                        self.click_sound.play()
                        selected_level_index = -1
                        for level_index in range(len(self._levels)):
                            if self._point_in_rect(event.pos,
                                                   self._levels_rect[level_index]):
                                selected_level_index = level_index
                                break
                        if selected_level_index >= 0:
                            self._play_game(
                                30,
                                self._levels[selected_level_index])
            self._clock.tick(5)

    def read_highscore(self):
        highscore = [0]
        file_path = os.path.join(get_activity_root(), 'data', 'highscore')
        if os.path.exists(file_path):
            with open(file_path, "r") as fp:
                highscore = fp.readlines()
        return int(highscore[0])

    def save_highscore(self):
        file_path = os.path.join(get_activity_root(), 'data', 'highscore')
        int_highscore = self.read_highscore()
        if not int_highscore > self.score:
            with open(file_path, "w") as fp:
                fp.write(str(self.score))

    def load_highscore(self):
        highscore = self.read_highscore()
        try:
            return highscore
        except (ValueError, IndexError) as e:
            logging.exception(e)
            return 0
        return 0

class PowerUpManager:
    """Manages power-ups and their activation."""
    def __init__(self):
        self.active_powerups = []

    def activate(self, powerup_name, duration, callback):
        """Activates a power-up for a specific duration."""
        self.active_powerups.append(powerup_name)
        pygame.time.set_timer(USEREVENT + len(self.active_powerups) + 10, duration * 1000)
        callback()

    def deactivate(self, powerup_name):
        """Deactivates a power-up."""
        if powerup_name in self.active_powerups:
            self.active_powerups.remove(powerup_name)

def main():
    pygame.init()
    pygame.display.set_mode((0, 0), pygame.RESIZABLE)
    game = Game() 
    game.show_menu()

if __name__ == '__main__':
    main()
