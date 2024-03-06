import threading, time

def check_fun(func):

    def inner(*args):

        thread_running = False
        print('args1:',args[0])
        print('args2:', args[1])
        """
        for th in threading.enumerate():
            if th.name == 'Signum':
                thread_running = True
                break
        if not thread_running :
            print('Starting sigmun thread')
            signum = threading.Thread(target=func, args=args, name='Signum')
            signum.start() 
            #return signum               
        else:
            print('Signum thread already running')
        """
        new_args = (args[0]+1, args[1])   
        #return func(*new_args)
        return None
    return inner


@check_fun
def test_fun(i,j):
    print('Thread started')
    
    while True:
        print('thread id:',threading.get_ident())
        print(i,j)
        time.sleep(4)

"""
for i in range(0,5,1):
    print('thread  ex id:',threading.get_ident())
    test_fun(i,i+10)
    time.sleep(4)

"""
print(test_fun(1,10))
