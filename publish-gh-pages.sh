#!/usr/bin/env bash

rsync -delete -rivd \
	 --include "*.html" --include "*.ttf" \
	 --exclude-from excludes.txt \
	. ../rsheeter.github.io/colorize/