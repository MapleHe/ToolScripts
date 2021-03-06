#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
    File:	TOTP_2FAGenerate.py
    Author: MapleHe
    Date:	2019-09-25
    ------
    The origin of 2FA algorithm: https://github.com/bdauvergne/python-oath.git (BSD 3-Clause LICENSE)
    ------
    Version: 2.1
'''

import sys
import os
import base64
import binascii
import hashlib
import time
import hmac
import struct
import platform
import argparse

PYVERSION = sys.version_info[0]
SYSTEM = platform.system()

if PYVERSION == 2:
    from urlparse import urlparse, parse_qs
else:
    from urllib.parse import urlparse, parse_qs


OTPAUTH="otpauth://totp/<username>%20<username>@<domain.cn>?secret=<XXXXXXXXXXXXXXXXXXXX>&issuer=ISSUER_NAME"
HOME = os.path.expanduser("~")

if SYSTEM == "Linux" or SYSTEM == "Darwin" or "CYGWIN" in SYSTEM.upper():
    if not os.path.exists(os.path.expanduser("~/.ssh")):
        print("~/.ssh/ directory doesn't exists.")
        sys.exit(0)
    EXPECTFILE = HOME + "/.ssh/auto_login.exp"
    OTPAUTHPATH = HOME + "/.ssh/TOTP_otpauth_key"
else:
    EXPECTFILE = "./auto_login.exp"
    OTPAUTHPATH = "./TOTP_otpauth_key"

LABEL   =   'label'
TYPE    =    'type'
ALGORITHM = 'algorithm'
DIGITS  =  'digits'
SECRET  =  'secret'
COUNTER = 'counter'
PERIOD  =  'period'
TOTP    =    'totp'
HOTP    =    'hotp'
DRIFT   =   'drift'
ISSUER  = 'issuer'

def fromhex(s):
    if PYVERSION == 2:
        return bytearray.fromhex(s)
    else:
        return bytes.fromhex(s)
def tohex(bin):
    return binascii.hexlify(bin).decode('ascii')

def lenient_b32decode(data):
    data = data.upper()  # Ensure correct case
    data += ('=' * ((8 - len(data)) % 8))  # Ensure correct padding
    return base64.b32decode(data.encode('ascii'))

def parse_otpauth(otpauth_uri):
    if not otpauth_uri.startswith('otpauth://'):
        raise ValueError('Invalid otpauth URI', otpauth_uri)

    # urlparse in python 2.6 can't handle the otpauth:// scheme, skip it
    parsed_uri = urlparse(otpauth_uri[8:])

    params = dict(((k, v[0]) for k, v in parse_qs(parsed_uri.query).items()))
    params[LABEL] = parsed_uri.path[1:]
    params[TYPE] = parsed_uri.hostname

    if SECRET not in params:
        raise ValueError('Missing secret field in otpauth URI', otpauth_uri)
    try:
        params[SECRET] = tohex(lenient_b32decode(params[SECRET]))
    except TypeError:
        raise ValueError('Invalid base32 encoding of the secret field in '
                         'otpauth URI', otpauth_uri)
    if ALGORITHM in params:
        params[ALGORITHM] = params[ALGORITHM].lower()
        if params[ALGORITHM] not in ('sha1', 'sha256', 'sha512', 'md5'):
            raise ValueError('Invalid value for algorithm field in otpauth '
                             'URI', otpauth_uri)
    else:
        params[ALGORITHM] = 'sha1'
    try:
        params[ALGORITHM] = getattr(hashlib, params[ALGORITHM])
    except AttributeError:
        raise ValueError('Unsupported algorithm %s in othauth URI' %
                         params[ALGORITHM], otpauth_uri)

    for key in (DIGITS, PERIOD, COUNTER):
        try:
            if key in params:
                params[key] = int(params[key])
        except ValueError:
            raise ValueError('Invalid value for field %s in otpauth URI, must '
                             'be a number' % key, otpauth_uri)
    if COUNTER not in params:
        params[COUNTER] = 0 # what else ?
    if DIGITS in params:
        if params[DIGITS] not in (6, 8):
            raise ValueError('Invalid value for field digits in othauth URI, it '
                             'must 6 or 8', otpauth_uri)
    else:
        params[DIGITS] = 6
    if params[TYPE] == HOTP and COUNTER not in params:
        raise ValueError('Missing field counter in otpauth URI, it is '
                         'mandatory with the hotp type', otpauth_uri)
    if params[TYPE] == TOTP and PERIOD not in params:
        params[PERIOD] = 30
    return params

def totp(key, format='dec6', period=30, t=None, hash=hashlib.sha1):
    '''
       Compute a TOTP value as prescribed by OATH specifications.
       :param key:
           the TOTP key given as an hexadecimal string
       :param format:
           the output format, can be:
              - hex, for a variable length hexadecimal format,
              - hex-notrunc, for a 40 characters hexadecimal non-truncated format,
              - dec4, for a 4 characters decimal format,
              - dec6,
              - dec7, or
              - dec8
           it defaults to dec6.
       :param period:
           a positive integer giving the period between changes of the OTP
           value, as seconds, it defaults to 30.
       :param t:
           a positive integer giving the current time as seconds since EPOCH
           (1st January 1970 at 00:00 GMT), if None we use time.time(); it
           defaults to None;
       :param hash:
           the hash module (usually from the hashlib package) to use,
           it defaults to hashlib.sha1.
       :returns:
           a string representation of the OTP value (as instructed by the format parameter).
       :type: str
    '''
    if t is None:
        t = int(time.time())
    else:
        import datetime, calendar
        if isinstance(t, datetime.datetime):
            t = calendar.timegm(t.utctimetuple())
        else:
            t = int(t)
    T = int(t/period)
    return hotp(key, T, format=format, hash=hash)

def truncated_value(h):
    v = h[-1]
    if not isinstance(v, int): v = ord(v) # Python 2.x
    offset = v & 0xF
    (value,) = struct.unpack('>I', h[offset:offset + 4])
    return value & 0x7FFFFFFF

def dec(h,p):
    digits = str(truncated_value(h))
    return digits[-p:].zfill(p)

def int2beint64(i):
    return struct.pack('>Q', int(i))

def __hotp(key, counter, hash=hashlib.sha1):
    bin_counter = int2beint64(counter)
    bin_key = fromhex(key)

    return hmac.new(bin_key, bin_counter, hash).digest()

def hotp(key,counter,format='dec6',hash=hashlib.sha1):
    '''
       Compute a HOTP value as prescribed by RFC4226
       :param key:
           the HOTP secret key given as an hexadecimal string
       :param counter:
           the OTP generation counter
       :param format:
           the output format, can be:
              - hex, for a variable length hexadecimal format,
              - hex-notrunc, for a 40 characters hexadecimal non-truncated format,
              - dec4, for a 4 characters decimal format,
              - dec6,
              - dec7, or
              - dec8
           it defaults to dec6.
       :param hash:
           the hash module (usually from the hashlib package) to use,
           it defaults to hashlib.sha1.
       :returns:
           a string representation of the OTP value (as instructed by the format parameter).
       Examples:
        >>> hotp('343434', 2, format='dec6')
            '791903'
    '''
    bin_hotp = __hotp(key, counter, hash)

    if format == 'dec4':
        return dec(bin_hotp, 4)
    elif format == 'dec6':
        return dec(bin_hotp, 6)
    elif format == 'dec7':
        return dec(bin_hotp, 7)
    elif format == 'dec8':
        return dec(bin_hotp, 8)
    elif format == 'hex':
        return '%x' % truncated_value(bin_hotp)
    elif format == 'hex-notrunc':
        return tohex(bin_hotp)
    elif format == 'bin':
        return bin_hotp
    elif format == 'dec':
        return str(truncated_value(bin_hotp))
    else:
        raise ValueError('unknown format')


def generate(otpauth_uri):
    parsed_otpauth_uri = parse_otpauth(otpauth_uri)
    format = 'dec%s' % parsed_otpauth_uri[DIGITS]
    hash = parsed_otpauth_uri[ALGORITHM]
    secret = parsed_otpauth_uri[SECRET]
    state = {}
    if parsed_otpauth_uri[TYPE] == HOTP:
        if COUNTER not in state:
            state[COUNTER] = parsed_otpauth_uri[COUNTER]
        otp = hotp(secret, state[COUNTER], format=format, hash=hash)
        state[COUNTER] += 1
        return otp
    elif parsed_otpauth_uri[TYPE] == TOTP:
        period = parsed_otpauth_uri[PERIOD]
        return totp(secret, format=format,
                         period=period,
                         hash=hash, t=None)
    else:
        raise NotImplementedError(parsed_otpauth_uri[TYPE])

def configFile(expectFilePath, username="username", password="PaSswOrd"):
    with open(expectFilePath, "wt") as _ot:
        _ot.write('''#!/usr/bin/expect -f
set username "''' + username + '''"
set serverip [lindex $argv 0]
set vcode [lindex $argv 1]
set passwd "''' + password + '''"
set logincount 0
set timeout -1
spawn ssh $username@$serverip
expect {
    "*assword:" {
        if { $logincount < 1 } {
            sleep 1
            send "$passwd\\r"; set logincount 2; exp_continue
        } else {
            send_user "\\n\\nLogin error. Try again later (too frequent). Or check the password or otpauth key. Or check the system time.\\n"; send \\x03;
        }
    }
    "*erification*code" {sleep 1; send "$vcode\\r"; exp_continue}
    "*login*"
}
interact
exit
''')

def argParser():
    parser = argparse.ArgumentParser(description="Generate 2FA verification code automatically.", epilog=usage(), formatter_class=argparse.RawTextHelpFormatter)    

    parser.add_argument(
        "-i", "--ip",
        type=str,
        required=False,
        default="127.0.0.1",
        help="Targeted ssh IP address."
    )

    parser.add_argument(
        "-f", "--keyfile",
        type=str,
        required=False,
        default=OTPAUTHPATH,
        help="The path of file to save OTP authentication seceret key."
    )

    parser.add_argument(
        "--config",
        action="store_true",
        required=False,
        help="Create configuration files in .ssh folder in User's HOME."
    )

    parser.add_argument(
        "-u", "--username",
        type=str,
        required=False,
        default="username",
        help="For configuration only. Login user's name for targeted ssh server."
    )

    parser.add_argument(
        "-p", "--password",
        type=str,
        required=False,
        default="PaSswOrd",
        help="For configuration only. Login user's password for targeted ssh server."
    )

    parser.add_argument(
        "-k", "--otpkey",
        type=str,
        required=False,
        default=OTPAUTH,
        help="For configuration only. OTP authentication secret key. Format: \"otpauth://totp/<username>%%20<username>@<domain.cn>?secret=<XXXXXXXXXXXXXXXXXXXXXXX>&issuer=ISSUER_NAME\""
    )

    return parser.parse_args()

def usage():
    usageInfo = "======================================================================\n" + \
"Support system: MacOS, Linux, Windows WSL/MobaXterm\n" + \
"Xshell and many other third-party softwares use pop-up window for 2FA code input. This scipt cannot help.\n\n" + \
"用法说明: \n" + \
"1. 先确保运行环境为 Linux-like。其中Windows下WSL保证已安装expect和Python3工具即可,MobaXterm工具则需要安装Python3和expect插件，然后创建 Shell session，即可使用ssh，expect以及Python。\n" + \
"2. 生成所需文件: python TOTP_2FAGenerate.py --config --username <user> --password <passwd> --otpkey \"otpauth://xxxx\" \n" + \
"3. 免密登录命令: \"expect -f ~/.ssh/auto_login.exp $(python3 TOTP_2FAGenerate.py -i <serverip> [-f ~/.ssh/TOTP_otpauth_key])\"\n\n" + \
"TOTPKEY获取方法：\n" + \
"1. 用离线二维码扫描器 (离线的安全一些，最好是手机自带的那种, 微信的扫一扫也可以) 扫个人专属的两步验证二维码(就是添加Authenticator时扫的那个).\n" + \
"2. 扫描完后选择复制内容/复制链接或者分享到记事本等, 以获取相应的文本. 当前支持的二维码内容是 otpauth://totp 开头的模式.\n" + \
"    (格式: otpauth://totp/<username>%20<username>@<domain.cn>?secret=<XXXXXXXXXXXXXXXXXXXXXXX>&issuer=ISSUER_NAME)\n" + \
"3. 将文本内容贴到 ~/.ssh/TOTP_otpauth_key 中, 然后就可以用最开始生成的exp脚本实现免密登录. 建议添加到 bashrc 的快捷命令中.\n\n" + \
"注意事项：\n" + \
"1. 如果登录失败请检查 ~/.ssh/TOTP_otpauth_key 文件和 ~/.ssh/auto_login.exp 脚本中的密码是否正确, 也可以再登录一次或者等一会再尝试, 可能因为当前的 2FA 是时间相关的算法, 频繁登录或者系统时间出错会导致登录失败.\n" + \
"2. 为避免时间因素导致的登录异常, 强烈建议使用 \"ssh通道复用\" 这一辅助方法，在 ~/.ssh/config 中为指定 host 添加 \"ControlMaster, ControlPath, ControlPersist\" 参数. 登录一次后, 后续的就不需要再登录. 具体如下：\n\n" + \
"Host *\n" + \
"    AddKeysToAgent yes\n" + \
"    UseKeychain yes\n" + \
"    IdentityFile ~/.ssh/id_rsa\n" + \
"    ControlMaster auto\n" + \
"    ControlPath ~/.ssh/master-%r@%h:%p\n" + \
"    ControlPersist 10\n"

    return usageInfo

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Execute \"python " + sys.argv[0] + " -h\" for help.")
        sys.exit(0)
    args = argParser()
    if (args.config):
        if (SYSTEM == "Linux" or SYSTEM == "Darwin" or "CYGWIN" in SYSTEM.upper()):
            configFile(EXPECTFILE, args.username, args.password)
        with open(args.keyfile, "wt") as _oth:
            _oth.write(args.otpkey)
        if (SYSTEM == "Windows"):
            print("\nOTP authentication key file is generated. File path: {0} .\n".format(args.keyfile))
        elif (SYSTEM == "Linux" or SYSTEM == "Darwin"):
            print("\nFile created:\nauto login file: ~/.ssh/auto_login.exp\nsecret key file: {0}\n".format(args.keyfile))
            print("\nLogin method: expect -f ~/.ssh/auto_login.exp $(python3 TOTP_2FAGenerate.py -i <serverIP> [-f <keyfile>])\n")
            print("\nRemember to check the username and password in ~/.ssh/auto_login.exp")
    else:
        authKey = args.otpkey
        with open(args.keyfile, "rt") as _otpa:
            authKey = _otpa.readline().rstrip()
        if (SYSTEM == "Windows"):
            print("{0}".format(generate(authKey)))
        else:
            print("{0} {1}".format(args.ip, generate(authKey)))

README='''
# Linux_server_2-Step_auto_login

**The script is based on <https://github.com/bdauvergne/python-oath.git>**

**Only support terminal that has `expect` command.**

**Only support TOTP algorithm currently. You can check the algorithm type in your OTPAUTH text by scanning 2FA QR-code. Example: `otpauth://totp/xxx`**

## Support system:

+ MacOS
+ Linux
+ Windows WSL

## 用法说明

Windows 的各种终端工具是自带的弹窗验证, 暂时无解.

初始化步骤:

1. 先用 `python3 TOTP_2FAGenerate.py --config -u cluster_username -p cluster_password -k "TOTPkey"` 命令生成所需文件.
2. 免密登录命令: `expect -f ~/.ssh/auto_login.exp $(python3 TOTP_2FAGenerate.py -i <serverip>)`

TOTPKEY获取方法：
1. 用离线二维码扫描器 (微信扫一扫也ok) 扫个人专属的两步验证二维码 (就是添加Authenticator时扫的那个).  (离线的安全一些) 
2. 扫描完后选择复制内容/复制链接或者分享到记事本等, 以获取相应的文本. 当前支持的二维码内容是 otpauth://totp 开头的模式. 参考格式:

    (`otpauth://totp/<username>%20<username>@<domain.cn>?secret=<XXXXXXXXXXXXXXXXXXXXXXX>&issuer=ISSUER_NAME`)

如果登录失败请检查 `~/.ssh/TOTP_otpauth_key` 文件中的 otpauth 内容是否正确, 以及 `~/.ssh/auto_login.exp` 中的集群用户名和密码是否正确。

辅助方法: 在 `~/.ssh/config` 中为指定 host 添加 "ControlMaster, ControlPath, ControlPersist" 参数，可以实现 ssh 通道的复用，登录一次后，后续的就不需要再登录。

## Usage

### Generate auto_login file

`python3 TOTP_2FAGenerate.py --config`

This will generate:

+ auto_login file: ~/.ssh/auto_login.exp
+ otpaupath file:  ~/.ssh/TOTP_otpauth_key

### Generate 2FA code

`python3 TOTP_2FAGenerate.py -i <serverip>`

This will output: <serverip> <2FA verification code>

### TOTP-2FA ssh Auto-login method

**utilizing linux "expect" program**

1. Generate config file.
2. Extract your `otpauth://` secret key from 2FA QR code. (just scan the QR and copy as text)
    
    example: `otpauth://totp/<username>%20<username>@<domain.cn>?secret=<XXXXXXXXXXXXXXXXXXXXXXX>&issuer=ISSUER_NAME`

3. Paste your secret URL to `TOTP_otpauth_key` file
4. Modify the user name and password in `auto_login.exp` file
5. Use the following command to login:

```Bash
expect -f ~/.ssh/auto_login.exp $(python3 TOTP_2FAGenerate.py -i <serverip>)
```

**Check your otpauth key or try the command again if fail to login as the algorithm is dependent on system time.**

## Other methods to avoid endless verification

Add "ControlMaster, ControlPath, ControlPersist" configure items to specific host in your ~/.ssh/config file. Which will build a special tunnel that can be re-used, then consequent ssh will use the same tunnel without login. 

```
Host *
 AddKeysToAgent yes
 UseKeychain yes
 IdentityFile ~/.ssh/id_rsa
 ControlMaster auto
 ControlPath ~/.ssh/master-%r@%h:%p
 ControlPersist 10
```

Then you can use the command to login:

```Bash
# this will check the existed ssh tunnel when you set ControlMaster in .ssh/config file.
if [ -S ~/.ssh/master-user@serverip:port ]; then ssh user@serverip:port; else expect -f ~/.ssh/auto_login.exp $(python3 TOTP_2FAGenerate.py -i <serverip>); fi 
```
'''
