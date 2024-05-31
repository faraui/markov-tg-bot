import config
import alt
import telebot
import time
import os, shutil
from itertools import chain
#import subprocess

algs_path = 'algs/'
bot = telebot.TeleBot(config.BOT_TOKEN)

FILE_CONTENT = 1
ENTRY = 2
RUNNING = 3
DDCONFIRM = 4
storage = {}
storage['waiting'] = None

class BadPath(BaseException):
    def __init__(self, path):
        self.path = path

def handle_waiting(func):
    def _wrapper(message):
        if storage['waiting']:
            if message.text == '!' and storage['waiting'] != RUNNING:
                storage['waiting'] = None
                bot.send_message(message.chat.id, 'Execution interrupted')
            elif storage['waiting'] == FILE_CONTENT:
                create_file(message)
            elif storage['waiting'] == ENTRY:
                exec_with_entry(message)
            elif storage['waiting'] == RUNNING:
                if message.text == '!':
                    alt.interrupt()
                else:
                    bot.send_message(message.chat.id, 'Executing...\nSend ! to interrupt')
            elif storage['waiting'] == DDCONFIRM:
                rmdir(message)
        else:
            func(message)
    return _wrapper

def handle_syntax(func):
    def _wrapper(message):
        try:
            func(message)
        except ValueError:
            welcome(message)
        except BadPath as e:
            bot.send_message(message.chat.id, 'Incorrect path %s' % e.path)
        except FileNotFoundError as e:
            bot.send_message(message.chat.id, '%s: no such file or directory' % e.filename.split('/', 1)[1])
        except IsADirectoryError as e:
            bot.send_message(message.chat.id, '%s: is a directory' % e.filename.split('/', 1)[1])
        except NotADirectoryError as e:
            bot.send_message(message.chat.id, '%s: is not a directory' % e.filename.split('/', 1)[1])
    return _wrapper

def check_path(path):
    if '..' in path: raise BadPath(path)
    for n in path:
        if n not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890-_/.':
            raise BadPath(path)
    return path


@bot.message_handler(commands=['help', 'start'])
@handle_waiting
def welcome(message):
    bot.reply_to(message, """
Help:
    /n /new [<path>/]<file name>
        - add new algorithm
    /x /exec [<path>/]<file name> *[[<path>/]<file name>]
        - execute one or many algorithms
    /py [<path>/]<file name> *[<аргументы>]
        - run Python script
    /l /list [<path>/]<file name>
        - list directory content
    /m /rename [<path>/]<file name> [<new path>/]<new file name>
        - rename and (or) relocate file
    /e /edit [<path>/]<file name>
        - edit file
    /c /cat [<path>/]<file name>
        - show file content
    /d /del [<path>/]<file name>
        - delete file
    /md /mkdir <path>
        - make directory
    /dd /rmdir <path>
        - delete directory AND the content of it
    /tree [<path>]
        - show directory structure-tree

    Allowed characters in names and paths:
        a-z, A-Z, 0-9, _, -
    Directories in a path are separated with /
    Now in the algs/ directory
    """)

@bot.message_handler(commands=['exec', 'x'])
@handle_waiting
@handle_syntax
def exec(message):
    _, *s = message.text.split()
    files = []
    for f in [check_path(n) for n in s]:
        if f.endswith('.alh'):
            h = open(algs_path + f).read().splitlines()
            for file in h:
                file = file.split('~')[0].strip()
                if file == '': continue
                try:
                    files.append(check_path(file))
                except Exception as e:
                    bot.reply_to(message, f'Error in algorithm {f}, string {h.index(file)}:')
                    raise e
        else: files.append(f)
    try:
        storage['codes'] = [alt.compile(open(algs_path + file).read(), file) for file in files]
        storage['waiting'] = ENTRY
        bot.reply_to(message, 'Waiting for input...\nSend ! to interrupt')
    except alt.CompileError as e:
        bot.reply_to(message, str(e))

def exec_with_entry(message):
    storage['waiting'] = RUNNING
    bot.reply_to(message, 'Executing...\nSend ! to interrupt')
    entry = message.text
    try:
        s_time = time.time()
        for code in storage['codes']:
            entry = alt.execute(code, entry)
        bot.send_message(message.chat.id, f'Output: {entry}\nExecution time: {time.time() - s_time:.10f}s')
    except alt.ExecutionInterrupt:
        bot.send_message(message.chat.id, 'Executing interrupted')
    except telebot.apihelper.ApiTelegramException as e:
        bot.send_message(message.chat.id, str(e))
    storage['waiting'] = ENTRY
    bot.send_message(message.chat.id, 'Waiting for input...\nSend ! to interrupt')

@bot.message_handler(commands=['py'])
@handle_waiting
@handle_syntax
def py(message):
    _, n, *s = message.text.split()
    path = check_path(n)
    #storage['task'] = PyExec(['python3', algs_path + path] + s)
    #storage['waiting'] = RUNNING
    #storage['task'].start()
    #storage['task'].join()
    #bot.reply_to(message, storage['task'].out, parse_mode='MarkdownV2')

import threading
class PyExec(threading.Thread):
    def __init__(self, e):
        self.e = e
    def run(self, e):
        self.out = '```\n' + subprocess.check_output(e) + '```'

@bot.message_handler(commands=['new', 'n'])
@handle_waiting
@handle_syntax
def new(message):
    _, n = message.text.split()
    storage['file'] = check_path(n)
    storage['waiting'] = FILE_CONTENT
    bot.send_message(message.chat.id, 'Waiting for file contents...\nSend ! to interrupt')

@bot.message_handler(commands=['edit', 'e'])
@handle_waiting
@handle_syntax
def edit(message):
    _, n = message.text.split()
    storage['file'] = check_path(n)
    code = open(algs_path + storage['file']).read()
    storage['waiting'] = FILE_CONTENT
    bot.send_message(message.chat.id, 'Waiting for a new file content...\nSend ! to interrupt')
    bot.send_message(message.chat.id, '```\n' + code + '```', parse_mode='MarkdownV2')

@handle_syntax
def create_file(message):
    storage['waiting'] = None
    open(algs_path + storage['file'], 'w').write(message.text)
    bot.send_message(message.chat.id, '%s file is added' % storage['file'])

@bot.message_handler(commands=['cat', 'c'])
@handle_waiting
@handle_syntax
def cat(message):
    _, n = message.text.split()
    path = check_path(n)
    code = open(algs_path + path).read()
    bot.send_message(message.chat.id, '%s file content:' % path)
    bot.send_message(message.chat.id, code)

@bot.message_handler(commands=['list', 'l'])
@handle_waiting
@handle_syntax
def list(message):
    _, n = (message.text.split()+[''])[:2]
    path = check_path(n)
    dirs, files = [], []
    for file in os.listdir(algs_path + path):
        if os.path.isfile(algs_path + os.path.join(path, file)):
            files.append(os.path.join(path, file))
        else:
            dirs.append(os.path.join(path, file))
    if dirs or files:
        ret = '%s directory content:\n' % path
        ret += '\n'.join(
            [f'({len(os.listdir(algs_path + dir)):>4}) {dir.rsplit("/", 1)[-1]}/' for dir in dirs] + \
            [f'     - {file.rsplit("/", 1)[-1]}' for file in files]
        )
        bot.reply_to(message, '```yaml\n' + ret + '```', parse_mode='MarkdownV2')
    else:
        bot.reply_to(message, '%s directory is empty' % path)

@bot.message_handler(commands=['rename', 'm'])
@handle_waiting
@handle_syntax
def rename(message):
    _, n, nn = message.text.split()
    path = check_path(n)
    new_path = check_path(nn)
    try:
        os.rename(algs_path + path, algs_path + new_path)
        bot.reply_to(message, 'Done')
    except (NotADirectoryError, IsADirectoryError):
        bot.reply_to(message, f'Error. Destination name is incorrect удалось переместить {path} в {new_path}. Целевое имя не верно.')

@bot.message_handler(commands=['del', 'd'])
@handle_waiting
@handle_syntax
def delete(message):
    _, n = message.text.split()
    path = check_path(n)
    os.remove(algs_path + path)
    bot.reply_to(message, '%s deleted' % path)

@bot.message_handler(commands=['mkdir', 'md'])
@handle_waiting
@handle_syntax
def mkdir(message):
    _, n = message.text.split()
    path = check_path(n)
    os.makedirs(algs_path + path)
    bot.reply_to(message, 'Done')

@bot.message_handler(commands=['rmdir', 'dd'])
@handle_waiting
@handle_syntax
def deldir(message):
    _, n = message.text.split()
    storage['path'] = check_path(n)
    bot.reply_to(message, 'Are you sure? [y/N]')
    storage['waiting'] = DDCONFIRM

@handle_syntax
def rmdir(message):
    storage['waiting'] = None
    if message.text == 'y':
        shutil.rmtree(algs_path + storage['path'])
        bot.reply_to(message, '%s directory and the content of it were delete' % storage['path'])
    else:
        bot.reply_to(message, 'Cancel')

@bot.message_handler(commands=['tree'])
@handle_waiting
@handle_syntax
def tree(message):
    _, n = (message.text.split() + ['.'])[:2]
    path = check_path(n)
    ret = ''
    for ppath, dirs, files in os.walk(algs_path + path):
        ppath = ppath.replace(algs_path, '', 1).replace(path, '', 1)
        c = '    '*ppath.count('/')
        if ppath: ret += f'\n{c}- {ppath.split("/")[-1]}'
        for file in files:
            ret += f'\n{c}    - {file}'
    bot.reply_to(message, '```yaml\nDirectory structure-tree:\n' + ret + '```', parse_mode='MarkdownV2')

@bot.message_handler()
@handle_waiting
@handle_syntax
def on_text(message):
    if not storage['waiting']: raise ValueError

bot.infinity_polling()
