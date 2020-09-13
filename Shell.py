import Swamipp as Swami
import os,datetime
import _thread, sys
import argparse
parser = argparse.ArgumentParser(description="Swami++")
parser.add_argument("file",nargs="?",type=str,help="file to be executed",default="")
args=parser.parse_args()
if args.file:
  try:
    code=open(args.file,"r").read()
    y=datetime.datetime.now()
    result,error=Swami.run(args.file,code)
    x=datetime.datetime.now()
    if error:
        print(error.toString(),sep="\n")
    else:
        print(f"\nExecuted with zero errors in {(x-y).total_seconds()} seconds")
  except KeyboardInterrupt:
    sys.exit()
  except Exception as e:
    print("Could not find file, or fatal error...",e)
  sys.exit()
def begin(s,r):
  return s[:len(r)]==r
print("Swami++ 2.7.1, type credits for more info")
directory="C:/Swamipp/Programs/"
def notepad(f):
    os.system("notepad.exe "+directory+f)
    return
while 1:
    command=input(">>> ")
    if command=="exit":
        break
    elif command=="credits":
        print("Developed By ClackHack, inspired by CodePulse")
    elif begin(command,"file "):
        f=command.replace("file ","")
        if not f.endswith(".spp"):
            print("Expected .spp file")
            continue
        try:
            open(directory+f,"r").read()
        except:
            open(directory+f,"w").write("")
        _thread.start_new_thread(notepad,(f,))
        #os.system("notepad.exe Programs/"+f)
    elif begin(command,"run "):
        f = command.replace("run ","")
        try:
            code=open(directory+f,"r").read()
            y=datetime.datetime.now()
            result,error=Swami.run(f,code)
            x=datetime.datetime.now()
            if error:
                print(error.toString(),sep="\n")
            else:
                print(f"\nExecuted with zero errors in {(x-y).total_seconds()} seconds")
        except KeyboardInterrupt:
          continue
        except Exception as e:
            print("Could not find file, or fatal error...",e)
    elif command=="repl":
        while 1:
            text=input("Swami++ > ")
            if text.strip()=="":
                continue
            if text=="exit":
                break
            try:
              result,error=Swami.run("<Shell>",text)
            except KeyboardInterrupt:
              continue
            if error:
                print(error.toString())
            elif result:
                if len(result.elements)==1:
                   print(repr(result.elements[0]))
                else:
                    for i in result.elements:
                        print(repr(i))
    elif command=="programs":
        f=os.listdir(directory.strip("/"))
        for p in f:
            print(p)
    elif begin(command,"delete"):
        f = command.replace("delete ","").strip()
        try:
            os.remove(directory+f)
        except:
            print("The file you specified was not found...")
    elif command=="help":
        print("Commands are file, run, programs, delete, repl, and exit\nCheck the github page for syntax support")
    else:
        print("Unkown command...\ntype help for help... ")
