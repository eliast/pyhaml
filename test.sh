#! /bin/sh

python haml.py < test/basic.haml | diff - test/basic.html
