#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# By Dheera Venkatraman [ http://dheera.net ]
# Released under the MIT license.

# Modified to use numpy for more efficient processing
# Original non-numpy version at https://github.com/dheera/python-termgraphics

from __future__ import absolute_import, division, print_function, unicode_literals

import math
import numpy as np
import os
import sys
import time

if sys.version_info >= (3,):
    unichr = chr

COLOR_BLACK = (0, 0, 0)
COLOR_RED = (255, 0, 0)
COLOR_GREEN = (0, 255, 0)
COLOR_YELLOW = (255, 255, 0)
COLOR_BLUE = (0, 0, 255)
COLOR_MAGENTA = (255, 0, 255)
COLOR_CYAN = (0, 255, 255)
COLOR_WHITE = (255, 255, 255)

COLOR_SUPPORT_1 = 0
COLOR_SUPPORT_16 = 1
COLOR_SUPPORT_256 = 2

MODE_UNICODE = 0
MODE_EASCII = 2

IMAGE_MONOCHROME = 0
IMAGE_UINT8 = 1
IMAGE_RGB_2X4 = 2

TABLE_EASCII = " '-'.*.|'~/~/F//-\\-~/>-&'\"\"\"/)//.\\\\\\_LLL'\"<C-=CC:\\-\\vD=D|Y|Y|)AH.!i!.ii|/\"/F/Fff//rkfPrkJJ/P/P/P//>brr>kl>&&*=fF/)vb/PPDJ)19/2/R.\\\\\\\\\\\\(=T([(((C=3-5cSct!919|7Ce,\\\\\\_\\\\\\i919i9(C|)\\\\+tv\\|719|7@9_L=L_LLL_=6[CEC[=;==c2ctJ]d=¿Z6E/\\;bsbsbj]SSd=66jj]bddsbJ]j]d]d8"

UNICODE_BRAILLE_MAP= [ \
    0b00000001,
    0b00001000,
    0b00000010,
    0b00010000,
    0b00000100,
    0b00100000,
    0b01000000,
    0b10000000,
]

class TermGraphics(object):
    def __init__(self, mode = MODE_UNICODE):
        """
        Initialization. This class takes no arguments.
        """
        self.shape = (0, 0)
        self.term_shape = (0, 0)
        self.update_shape()
        self.current_color = np.array([255, 255, 255], dtype = np.uint8)
        self.mode = mode

        if self.term_type in ['xterm-256color', 'xterm']:
          self.color_support = COLOR_SUPPORT_256
        else:
          self.color_support = COLOR_SUPPORT_16

    def _rgb_to_8(self, rgb):
        return (rgb[2] > 127) << 2 | (rgb[1] > 127)<<1 | (rgb[0] > 127)

    def clear(self):
        """
        Clear the graphics buffer.
        """
        self.buffer &= 0
        self.buffer |= 0x2800
        self.colors &= 0
        self.buffer_text &= 0

    def update_shape(self):
        """
        Fetches the terminal shape. Returns True if the shape has changed.
        """
        self.term_shape = tuple(reversed(list(map(lambda x: int(x), os.popen('stty size', 'r').read().split()))))
        self.term_type = os.environ['TERM']
        new_shape = (self.term_shape[0]*2, self.term_shape[1]*4)
        if new_shape != self.shape:
            self.shape = (self.term_shape[0]*2, self.term_shape[1]*4)
            self.buffer = np.frombuffer((b'\x28\x00' * (self.term_shape[0] * self.term_shape[1])), dtype = np.uint16).reshape((self.term_shape[0], self.term_shape[1])).copy()
            self.colors = np.frombuffer((b'\xff\xff\xff' * (self.term_shape[0] * self.term_shape[1])), dtype = np.uint8).reshape((self.term_shape[0], self.term_shape[1], 3)).copy()
            self.buffer_text = np.frombuffer((b'\x00' * (self.term_shape[0] * self.term_shape[1])), dtype = np.uint8).reshape((self.term_shape[0], self.term_shape[1])).copy()
            return True
        return False

    def set_color(self, color):
        self.current_color = color

    def points(self, points, clear_block = False):
        """
        Draws a list of points = [(x0,y0), (x1,y1), (x2,y2), ...].
        """
        for point in points:
            self.point(point, clear_block = clear_block)
        for point in points:
            self.point(point, clear_block = False)

    def point(self, point, clear_block = False):
        """
        Draw a point at points = (x,y) where x is the column number, y is the row number, and (0,0)
        is the top-left corner of the screen.
        """
        if type(point[0]) is not int or type(point[1]) is not int:
            point = (int(point[0]), int(point[1]))

        if point[0] >= 0 and point[1] >= 0 and point[0] < self.shape[0] and point[1] < self.shape[1]:
            i, j = point[0] >> 1, point[1] >> 2
            if clear_block:
                self.buffer[i, j] = 0x2800 | UNICODE_BRAILLE_MAP[(point[0] & 0b1) | ((point[1] & 0b11) << 1)]
            else:
                self.buffer[i, j] = 0x2800 | (self.buffer[i, j] & 0xFF) | \
                  UNICODE_BRAILLE_MAP[(point[0] & 0b1) | ((point[1] & 0b11) << 1)]
            self.colors[i, j, :] = self.current_color

    def text(self, text, point):
        """
        Draws text at point = (x0, y0).
        """
        i, j = point[0] >> 1, point[1] >> 2
        if j >= self.term_shape[1]:
            return
        text = text[0:self.term_shape[0] - point[0]]
        self.buffer[i:i+len(text), j] = np.frombuffer(text.encode(), dtype = np.uint8)
        self.colors[i:i+len(text), j, :] = self.current_color

    def poly(self, points):
        """
        Draws lines between a list of points = [(x0,y0), (x1,y1), (x2,y2), ...].
        """
        for i in range(1, len(points)):
            self.line(points[i-1], points[i])

    def line(self, point0, point1):
        """
        Draw a line between point0 = (x0, y0) and point1 = (x1, y1).
        """
        if point1[0] == point0[0]:
            if point0[1] < point1[1]:
                for y in range(point0[1], point1[1]):
                    self.point((point0[0], y))
            else:
                for y in range(point1[1], point0[1]):
                    self.point((point0[0], y))
            return
        slope = (point1[1] - point0[1]) / (point1[0] - point0[0])
        if abs(slope) <= 1:
            if point0[0] < point1[0]:
                for x in range(point0[0], point1[0]):
                     self.point((x, point0[1] + slope*(x - point0[0])))
            else:
                for x in range(point1[0], point0[0]):
                     self.point((x, point0[1] + slope*(x - point0[0])))
        else:
            if point0[1] < point1[1]:
                for y in range(point0[1], point1[1]):
                     self.point((point0[0] + (y - point0[1])/slope, y))
            else:
                for y in range(point1[1], point0[1]):
                     self.point((point0[0] + (y - point0[1])/slope, y))
        return

    def rect(self, point0, point1):
        """
        Draw a rectangle between corners point0 = (x0, y0) and point1 = (x1, y1).
        """
        self.line((point0[0], point0[1]), (point0[0], point1[1]))
        self.line((point0[0], point1[1]), (point1[0], point1[1]))
        self.line((point1[0], point1[1]), (point1[0], point0[1]))
        self.line((point1[0], point0[1]), (point0[0], point0[1]))

    def image(self, data, width, height, point, image_type = IMAGE_MONOCHROME):
        """
        Draw a binary image with the top-left corner at point = (x0, y0).
        """
        if image_type == IMAGE_MONOCHROME:
            for i in range(width):
                for j in range(height):
                    if data[j*width + i] > 0:
                        self.point((point[0] + i, point[1] + j))

        elif image_type == IMAGE_UINT8:
            for i in range(width):
                for j in range(height):
                    if data[j*width + i] > 127:
                        self.point((point[0] + i, point[1] + j))

        elif image_type == IMAGE_RGB_2X4 and self.mode == MODE_UNICODE:
            for i in range(width):
                for j in range(height):
                    self.colors[i, j, :] = data[j*width + i]
                    self.buffer[i, j] = 0x2588

    def draw(self):
        """
        Shows the graphics buffer on the screen. Must be called in order to see output.
        """
        sys.stdout.write("\033[H")

        current_draw_color = -1

        for j in range(self.term_shape[1]):
            sys.stdout.write("\033[" + str(j+1) + ";1H")

            for i in range(self.term_shape[0]):
                if np.any(self.colors[i, j, :] != current_draw_color):
                    current_draw_color = self.colors[i, j, :]
                    if self.color_support == COLOR_SUPPORT_256:
                      sys.stdout.write("\033[38;2;{};{};{}m".format(current_draw_color[0], current_draw_color[1], current_draw_color[2]))
                    else:
                      sys.stdout.write("\033[3" + str(self._rgb_to_8(current_draw_color)) + "m")
                #if False and self.buffer_text[i, j]:
                #    sys.stdout.write(chr(self.buffer_text[i, j]))
                #else:
                if self.mode == MODE_UNICODE:
                    sys.stdout.write(unichr(self.buffer[i, j]))
                elif self.mode == MODE_EASCII:
                    if self.buffer[i, j] & 0xFF00 == 0x2800:
                        sys.stdout.write(TABLE_EASCII[self.buffer[i, j] & 0x00FF])
                    elif self.buffer[i, j] & 0xFF00 == 0x00 and self.buffer[i, j] & 0x00FF != 0x00:
                        sys.stdout.write(self.buffer[i, j])
                    else:
                        sys.stdout.write(0x20)
        sys.stdout.write("\033[37m")
        sys.stdout.flush()


if __name__ == '__main__':
    # perform a test if run directly
    g = TermGraphics()
    for j in range(10):
        g.clear()
        for i in range(300):
            g.point((i, int(i*j/5)))
        g.text("hello", (10, 10))
        g.draw()
        time.sleep(0.1)
