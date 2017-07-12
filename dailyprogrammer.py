#!/usr/bin/env python3

import argparse
from configparser import ConfigParser
from datetime import datetime
from email.message import EmailMessage
from mailbox import Maildir
import os
import re
import sys

import praw


def message_exists(mailbox, msg):
    for _, m in mailbox.items():
        if m.get('X-reddit-url', None) == msg['X-reddit-url']:
            return True
    return False


def save_challenge(challenge, mailbox):
    msg = EmailMessage()

    msg['Subject'] = challenge['title']
    msg['From'] = '{} <{}>'.format(challenge['author'].name, challenge['author'].fullname)
    msg['To'] = 'dailyprogrammer'
    msg['Date'] = challenge['date']
    msg['X-reddit-id'] = challenge['id']
    msg['X-reddit-url'] = challenge['url']
    msg['X-dailyprogrammer-number'] = challenge['number']
    msg['X-dailyprogrammer-level'] = challenge['level']

    msg.set_content('''{level}
{title}
{date} - #{number}
{url}

{text}
'''.format(**challenge))

    if not message_exists(mailbox, msg):
        mailbox.add(msg)

    mailbox.close()


def read_dailyprogrammer(config, limit=5, today_only=True):
    # This is the format used currently.
    challenge_re = re.compile(r'^\[(\d{4}-\d{2}-\d{2})\]\s+Challenge\s+#(\d+)\s+\[(\w+)\]\s+(.+)$')

    reddit = praw.Reddit(client_id=config['client_id'],
                         client_secret=config['secret'],
                         user_agent=config['user_agent'])
    wanted = config['levels'][:]

    challenges = {}

    for submission in reddit.subreddit('dailyprogrammer').new(limit=limit):
        m = challenge_re.match(submission.title)
        if m:
            level = m.group(3).lower()

            if level in wanted:
                year, month, day = m.group(1).split('-')
                challenges.setdefault(level, []).append({
                    'id':     submission.id,
                    'url':    submission.url,
                    'author': submission.author,
                    'level':  level,
                    'date':   datetime(int(year), int(month), int(day)),
                    'number': m.group(2),
                    'title':  m.group(4),
                    'text':   submission.selftext
                })

                if today_only:
                    wanted.remove(level)

                    if not wanted:
                        break

    return challenges


def get_config(filename):
    '''Read config from ini file

    The client_id, secret, and user_agent must be set.
    levels is a comma separated list. White space will be chopped.

    Here is a sample config:
    [config]
    client_id = abc123
    secret = ABC123ABC123
    user_agent = linux:com.github.shaleh.dailyprogrammer:0.1.0 (by /u/shaleh)
    levels = intermediate,hard
    '''
    parser = ConfigParser(interpolation=None)
    parser.read(filename)

    config = {}

    required = ['client_id', 'secret', 'user_agent']
    for i in required:
        config[i] = parser.get('config', i)
    levels = parser.get('config', 'levels', fallback='easy,intermediate,hard')
    config['levels'] = [ x.strip() for x in levels.split(',') ]

    return config


def main(argv):
    parser = argparse.ArgumentParser(description="/r/dailyprogrammer as email")

    parser.add_argument('-c', '--config', required=True)
    parser.add_argument('-l', '--limit', type=int, default=10)
    parser.add_argument('--today', action='store_true', default=False)
    parser.add_argument('maildir')

    args = parser.parse_args(argv)

    config = get_config(args.config)

    mailbox = Maildir(args.maildir, create=(not os.path.isdir(args.maildir)))

    challenges = read_dailyprogrammer(config, limit=args.limit, today_only=args.today)

    for level in config['levels']:
        if level in challenges:
            for i in challenges[level]:
                save_challenge(i, mailbox)


if __name__ == '__main__':
    main(sys.argv[1:])
