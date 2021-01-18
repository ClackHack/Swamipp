@echo off
pyinstaller File.py --onefile && pyinstaller Shell.py --onefile
RMDIR /S /Q C:\Users\Clay\Clay\Python\Swamipp\build
RMDIR /S /Q C:\Users\Clay\Clay\Python\Swamipp\File.spec
RMDIR /S /Q C:\Users\Clay\Clay\Python\Swamipp\Shell.spec