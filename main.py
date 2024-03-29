# -*- coding: utf-8 -*-
import vklogic as vkl

from chatbot import chatbot
from utils import parse_input

from io import BytesIO
import configparser
import random
import pycurl
import time
import json
import re
import os

config = configparser.ConfigParser()
rootDir = os.getcwd()
modelDir = os.path.join(rootDir, 'save/model')
configName = os.path.join(modelDir, 'params.ini')
config.read(configName)

__version__ = '0.0.3'
__author__ = 'Eugene Ershov - http://vk.com/fogapod'
__source__ = 'https://github.com/Fogapod/ChatBot/'

try:
	__rang__ = config['General'].getint('globStep')
except:
	__rang__ = False

__info__ = '''
Версия: {ver}
Шагов обучения: {rang}

Я умею:
*Говорить то, что вы попросите
(/say ... |/скажи ... )
*Вызывать помощь
(/help |/помощь )
*Вести диалог
(/... )

В конце моих сообщений ставится знак верхней кавычки'

Автор: {author}
Мой исходный код: {source}
'''.format(\
	ver=__version__, author=__author__, rang=__rang__, source=__source__
)

def animate_loading(text, delay):
	loading_symbols = ('|', '/', '-', '\\')
	for i, symbol in enumerate(loading_symbols):
		print('#{} {}\r'.format(text, symbol), end='')
		time.sleep(delay/len(loading_symbols))

def main():
	client = vkl.Client()
	
	while not client.authorization():
		continue

	client.save_full_message_history()

	cb = chatbot.Chatbot()
	cb.main()

	print(__info__)

	url = client.make_url()
	c = pycurl.Curl()
	m = pycurl.CurlMulti()

	last_rnd_id = 1
	reply_count = 0
	while True:
		s = BytesIO()
		c.setopt(c.URL, url)
		c.setopt(c.WRITEFUNCTION, s.write)
		m.add_handle(c)

		while True:
			ret, num_handles = m.perform()
			if ret != pycurl.E_CALL_MULTI_PERFORM:
				break

		while num_handles: # main loop
			animate_loading(
				'Listening long poll... {} {ans}'.format(
					reply_count,
					ans = 'answer' if reply_count == 1 else 'answers'
				), 1
			)
			while 1: # main loop (2)
				ret, num_handles = m.perform()
				if ret != pycurl.E_CALL_MULTI_PERFORM:
					break

		m.remove_handle(c)
		response = s.getvalue()
		response = response.decode('utf-8')
		response = json.loads(response)

		url = client.make_url(keep_ts=response['ts'])

		for update in response['updates']:
			if update[0] == 4 and\
					update[7] !=\
					last_rnd_id and\
					update[6] != '':
			# response == message
			# message != last_message
			# message != ''
				text = update[6]
				mark_msg = True

				if re.sub('^( )*', '', text).startswith('/'):	
					text = text[1:]
					if text.startswith('/'):
						mark_msg = False
						text = text[1:]

					text = parse_input(text, replace_vkurl=False, replace_nl=False)
					words = text.split()

					if not words: 
						words = ' '

					if re.match('^((help)|(помощь)|(info)|(инфо)|(информация)|\?)',\
							words[0].lower()):
						text = __info__
					elif re.match('^((скажи)|(say))', words[0].lower()):
						del words[0]
						text = ' '.join(words)
					else:
						text = re.sub('(__nm__)|(__nl__)', '\n', cb.daemonPredict(text))

				else:
					continue

				last_rnd_id = update[7] + 1
				client.reply(
					uid = update[3],
					text = text + "'" if mark_msg else text,
					rnd_id = last_rnd_id
				)
				reply_count += 1

if __name__ == '__main__':
	main()