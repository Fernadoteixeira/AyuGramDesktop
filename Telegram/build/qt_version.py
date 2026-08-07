import sys, os

def resolve(arch):
    if sys.platform == 'darwin':
        os.environ['QT'] = '6.8.4'
    elif sys.platform == 'win32':
        if arch == 'arm' or 'qt6' in sys.argv:
            print('Choosing Qt 6.')
            os.environ['QT'] = '6.11.0'
        else:
            print('Choosing Qt 6.')
            os.environ['QT'] = '6.8.4'
    return True
