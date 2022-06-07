# The Makefile that can be used to build distributable versions of this web
# application, among other things.
#
# Copyright (C) 2022 by James MacKay.
#
#-This program is free software: you can redistribute it and/or modify
#-it under the terms of the GNU General Public License as published by
#-the Free Software Foundation, either version 3 of the License, or
#-(at your option) any later version.
#
#-This program is distributed in the hope that it will be useful,
#-but WITHOUT ANY WARRANTY; without even the implied warranty of
#-MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#-GNU General Public License for more details.
#
#-You should have received a copy of the GNU General Public License
#-along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

##
## Configuration.
##

# Names.
APP_NAME = ColourGrid
VERSION = 1.0
VERSIONED_APP_NAME = $(APP_NAME)-$(VERSION)

# Directories.
VIRTUALENV_DIR = venv
DIST_DIR = dist
EGG_INFO_DIR = $(APP_NAME).egg-info
    # created as part of building a distributable version of us
PYCACHE_DIR = __pycache__

# Files.
ACTIVATE_VENV_SCRIPT = bin/activate
    # relative to the root of the virtual environment to be activated
APP_DIST_FILE = $(DIST_DIR)/$(VERSIONED_APP_NAME).tar.gz
SETUP_SCRIPT = setup.py

README_BASE = README
README_ORG = $(README_BASE).org
README_TXT = $(README_BASE).txt
EXPORTED_DOCS = $(README_TXT)
    # note that README_ORG is the *original*, not an exported version

# Groups of files
SRC_FILES = *.py

# Programs and scripts.
CD = cd
COMMAND = command
CVS = cvs
EMACS = emacs
ERASE = rm -rf
GREP = grep
LN = ln
MV = mv
PYTHON = python3
RM = rm
SED = sed
SOURCE = source
TAR = tar


# Program options.
EMACS_ORG_EXPORT_OPTS = -nw --batch --eval


##
## Rules.
##

# Targets whose names are NOT the names of files.
.PHONY: dev prod docs
.PHONY: install
.PHONY: help help2
.PHONY: clean realclean

# Default rule (because it's first).
app: $(APP_DIST_FILE) ## creates a distributable version of our application

# Note: if we don't build README.txt then 'setup.py sdist' will complain
# about its absence.
$(APP_DIST_FILE): $(SRC_FILES) $(EXPORTED_DOCS)
	$(PYTHON) $(SETUP_SCRIPT) sdist


docs: $(README_TXT)  ## generates all of the documentation

# Put a single space at the end of sentences and don't indent text under a
# heading to reflect the heading level.
$(README_TXT): $(README_ORG)
	@if $(COMMAND) -v $(EMACS); then \
	    $(EMACS) $(EMACS_ORG_EXPORT_OPTS) \
	        "(progn \
	             (setq sentence-end-double-space nil \
	                   org-adapt-indentation nil) \
	             (find-file \"$(README_ORG)\") \
	             (org-ascii-export-to-ascii nil nil nil nil \
	                 (quote (:ascii-charset utf-8))) \
	             (kill-buffer))" \
	#else \
	#    echo "Could not build $(README_TXT): '$(EMACS)' not on PATH." \
	fi


# Note: unlike most of the rules here, this one is intended to at least
# potentially be used by the end user.
install: $(VIRTUALENV_DIR)  ## installs our application (for a user)
	# We intentionally combine the activation of the virtual environment and
	# the installing of the application in one command line so that they're
	# executed in the same shell. Unfortunately that shell is a subshell, so
	# we have to instruct the user to activate the virtual environment again
	# manually.
	$(COMMAND) $(SOURCE) $(VIRTUALENV_DIR)/$(ACTIVATE_VENV_SCRIPT) && \
		$(PYTHON) $(SETUP_SCRIPT) install
	@echo
	@echo "NOTE: before running ./colours.py you need to activate its virtual"
	@echo "environment by running the command"
	@echo
	@echo "  source $(VIRTUALENV_DIR)/$(ACTIVATE_VENV_SCRIPT)"
	@echo
	@echo "if the environment isn't already activated."
	@echo
	@echo "Then you can run ./colours.py to start the web application."
	@echo

$(VIRTUALENV_DIR):
	$(PYTHON) -m venv $(VIRTUALENV_DIR)


# Note: a rule's help text is assumed to follow a pair of consecutive '#'s on
# the same line as a rule name.
#
# Put 'sort' in the rule body right before 'awk' if you want our output
# sorted in alphabetical order by rule name.
#
# From: https://news.ycombinator.com/item?id=11939200
help:  ## outputs this help message
	@echo
	@grep -P '^[a-zA-Z_-]+:.*?#[#] .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?#[#] "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo

help2:  ## outputs a simpler version of the help message
	@echo
	@awk -F ':.*#[#]' '$$0 ~ FS {printf "%15s%s\n", $$1 ":", $$2}' $(MAKEFILE_LIST) # | sort
	@echo


clean:  ## deletes files that are expendable or can be quickly regenerated
	$(RM) -f *~
	$(PYTHON) $(SETUP_SCRIPT) clean

realclean: clean  ## deletes files that are expendable or can be regenerated
	$(ERASE) $(DIST_DIR) $(EGG_INFO_DIR) $(EXPORTED_DOCS)

# Note: the things that we only delete here (and not under 'realclean') are
# things that are at least somewhat painful to regenerate and that we rarely
# want to get rid of.
pristine: realclean  ## restores things to their original, freshly-installed state
	$(ERASE) $(VIRTUALENV_DIR) $(PYCACHE_DIR)
