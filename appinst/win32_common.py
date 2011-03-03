# Copyright (c) 2008 by Enthought, Inc.
# All rights reserved.

import _winreg
import platform
import sys
from os.path import abspath, isfile

import wininst


# Constants
CURRENT_USER = 0
ALL_USERS = 1


def _get_install_type():
    hklm = _winreg.ConnectRegistry(None, _winreg.HKEY_LOCAL_MACHINE)

    python_reg_path = ("SOFTWARE\\Python\\PythonCore\\%d.%d\\InstallPath"
                           % (sys.version_info[0], sys.version_info[1]))

    # Look for the python install for all users
    try:
        all_users_key = _winreg.OpenKey(
            hklm,
            python_reg_path,
            0,
            _winreg.KEY_READ)
    except EnvironmentError:
        all_users_key = None

    # Look for the python install for the current user
    try:
        hkcu = _winreg.ConnectRegistry(None, _winreg.HKEY_CURRENT_USER)
        current_user_key = _winreg.OpenKey(
            hkcu,
            python_reg_path,
            0,
            _winreg.KEY_READ)
    except EnvironmentError:
        current_user_key = None

    # if both keys are valid, we need to use sys.prefix to match against
    # the install path
    install_type = None
    if (all_users_key is not None) and (current_user_key is not None):
        all_users_install_path = _winreg.QueryValue(all_users_key, None)
        current_user_install_path = _winreg.QueryValue(current_user_key, None)

        if abspath(sys.prefix) == abspath(all_users_install_path):
            install_type = ALL_USERS

        if abspath(sys.prefix) == abspath(current_user_install_path):
            install_type = CURRENT_USER

    elif all_users_key is not None:
        install_type = ALL_USERS
    else:
        install_type = CURRENT_USER

    _winreg.CloseKey(hklm)
    _winreg.CloseKey(hkcu)

    # if we were not able to determine whether python was installed for all
    # users or just the current user, default to the current user
    if install_type is None:
        install_type = CURRENT_USER

    return install_type


def refreshEnvironment():
    HWND_BROADCAST = 0xFFFF
    WM_SETTINGCHANGE = 0x001A
    SMTO_ABORTIFHUNG = 0x0002
    sParam = "Environment"

    import win32gui
    res1, res2 = win32gui.SendMessageTimeout(HWND_BROADCAST, WM_SETTINGCHANGE,
                                             0, sParam, SMTO_ABORTIFHUNG, 100)


def append_to_reg_path(new_dir):
    """
    appends a new dir to the registry PATH value
    """
    # determine where the environment registry settings are
    if _get_install_type() == ALL_USERS:
        reg = _winreg.ConnectRegistry(None, _winreg.HKEY_LOCAL_MACHINE)
        environ_key_path = ('SYSTEM\\CurrentControlSet\\Control\\'
                            'Session Manager\\Environment')
    else:
        reg = _winreg.ConnectRegistry(None, _winreg.HKEY_CURRENT_USER)
        environ_key_path = "Environment"

    # open key for reading, to save and print out old value
    try:
        key = _winreg.OpenKey(reg, environ_key_path)
        old_path = _winreg.QueryValueEx(key, "Path")[0]
        _winreg.CloseKey(key)
    except WindowsError:
        old_path = ""

    # reopen key for writing new value
    key = _winreg.OpenKey(reg, environ_key_path, 0, _winreg.KEY_ALL_ACCESS)

    #  Check if the new dir has already been included in the old 'path' value
    path_exists = False
    for path_dir in old_path.split(';'):
        if path_dir.lower() == new_dir.lower():
            path_exists = True

    if not path_exists:
        new_path = "%s;%s" % (old_path.strip(';'), new_dir)

        # append new_dir to the PATH
        _winreg.SetValueEx(key, "Path", 0, _winreg.REG_EXPAND_SZ, new_path)

    _winreg.CloseKey(key)
    _winreg.CloseKey(reg)

    if not path_exists:
        try:
            refreshEnvironment()
        except:
            print "WARNING: The registry has been modified."
            print "You may need to restart your Windows session in order for "
            print "the changes to be seen by the application."


def append_to_reg_pathext():
    """
    appends .py and .pyc to the registry PATHEXT value
    """
    install_type = _get_install_type()

    # determine where the environment registry settings are
    if install_type == ALL_USERS:
        reg = _winreg.ConnectRegistry( None, _winreg.HKEY_LOCAL_MACHINE )
        environ_key_path = ("SYSTEM\\CurrentControlSet\\Control\\"
            "Session Manager\\Environment")
    else:
        reg = _winreg.ConnectRegistry( None, _winreg.HKEY_CURRENT_USER )
        environ_key_path = "Environment"

    # open key for reading, to save and print out old value
    try:
        key = _winreg.OpenKey(reg, environ_key_path )
        old_pathext = _winreg.QueryValueEx( key, "PATHEXT" )[0]
        _winreg.CloseKey( key )
    except WindowsError:
        if install_type == ALL_USERS:
            old_pathext = ""
        else:
            # use the system PATHEXT as the old value
            hklm_reg = _winreg.ConnectRegistry( None,
                _winreg.HKEY_LOCAL_MACHINE )
            try:
                key = _winreg.OpenKey(hklm_reg, (
                        "SYSTEM\\CurrentControlSet\\"
                        "Control\\Session Manager\\Environment"))
                old_pathext = _winreg.QueryValueEx( key, "PATHEXT" )[0]
                _winreg.CloseKey( key )
            except WindowsError:
                old_pathext=""
            _winreg.CloseKey( hklm_reg )

    # reopen key for writing new value
    key = _winreg.OpenKey(reg, environ_key_path, 0, _winreg.KEY_ALL_ACCESS)
    new_pathext = old_pathext + ";.PY;.PYC"
    _winreg.SetValueEx(key, "PATHEXT", 0, _winreg.REG_SZ, new_pathext)

    _winreg.CloseKey(key)
    _winreg.CloseKey(reg)

    try:
        refreshEnvironment()
    except:
        print "WARNING: The registry has been modified."
        print "You may need to restart your Windows session in order for the"
        print "changes to be seen by the application."



def remove_from_reg_path(remove_dir, install_mode='user') :
    """
    Removes a directory from the PATH environment variable. If the directory
    exists more than once on the path, all instances of that directory are
    removed.

    remove_dir      The directory to be removed from the PATH.
    install_mode    Determines which environment to modify. If 'system' is
                    given, the PATH variable in HKLM is modified. If 'user'
                    is given, the PATH variable in HKCU is modified.
    """
    if platform.uname()[0] != 'Windows':
        return

    # determine where the environment registry settings are
    if install_mode == 'system':
        reg = _winreg.ConnectRegistry(None, _winreg.HKEY_LOCAL_MACHINE)
        environ_key_path = ("SYSTEM\\CurrentControlSet\\Control\\"
                            "Session Manager\\Environment")
    else:
        reg = _winreg.ConnectRegistry(None, _winreg.HKEY_CURRENT_USER)
        environ_key_path = "Environment"

    # open key for reading, to save and print out old value
    key = _winreg.OpenKey(reg, environ_key_path)
    old_path = _winreg.QueryValueEx(key, "Path")[0]
    _winreg.CloseKey(key)

    # reopen key for writing new value
    key = _winreg.OpenKey(reg,environ_key_path, 0, _winreg.KEY_ALL_ACCESS)

    # create new path which omits the path we want to remove
    changed_path_value = False
    new_path = ""
    for path in old_path.split( ';' ):
        if path.lower() == remove_dir.lower():
            changed_path_value = True
        else:
            new_path += path + ';'

    # Remove the trailing semicolon
    new_path = new_path[:-1]

    # assign new_path to the PATH only if the old_path has been modified.
    if changed_path_value:
        _winreg.SetValueEx( key, "Path", 0, _winreg.REG_EXPAND_SZ, new_path )

    _winreg.CloseKey( key )
    _winreg.CloseKey( reg )

    if changed_path_value:
        try:
            refreshEnvironment()
        except:
            print "WARNING: The registry has been modified."
            print "You may need to restart your Windows session in order for "
            print "the changes to be seen by the application."


def register_association_with_shell(desc, cmd):
    """
    Adds command to shell association for .py files, enabling
    right clicking to edit the file
    """

    if platform.uname()[0] != 'Windows':
        return

    # determine where the shell registry settings are
    if _get_install_type() == ALL_USERS:
        reg = _winreg.ConnectRegistry(None, _winreg.HKEY_LOCAL_MACHINE)
        shell_key_path = r"SOFTWARE\Classes\Python.File\shell"
    else:
        reg = _winreg.ConnectRegistry(None, _winreg.HKEY_CURRENT_USER)
        shell_key_path = r"Software\Classes\Python.File\shell"

    reg = _winreg.ConnectRegistry(None, _winreg.HKEY_LOCAL_MACHINE)

    # open key for writing
    key = _winreg.OpenKey(reg, shell_key_path, 0, _winreg.KEY_ALL_ACCESS)
    new_key = _winreg.CreateKey(key, desc)
    _winreg.SetValue(new_key, "command", _winreg.REG_SZ, cmd)

    _winreg.CloseKey(new_key)
    _winreg.CloseKey(key)
    _winreg.CloseKey(reg)
