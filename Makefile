.PHONY: help start stop restart status test security-check security-audit
PROFILE ?= quick

help:
	./knowledgeforward help

start:
	./knowledgeforward start

stop:
	./knowledgeforward stop

restart:
	./knowledgeforward restart

status:
	./knowledgeforward status

test:
	./knowledgeforward test

security-check:
	./knowledgeforward security-check

security-audit:
	./knowledgeforward security-audit $(PROFILE)
