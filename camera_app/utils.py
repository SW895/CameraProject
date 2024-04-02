import threading


def check_thread(target_function):

    def inner(*args, **kwargs):

        thread_running = False

        for th in threading.enumerate():
            if th.name == args[0]:
                thread_running = True
                break

        if not thread_running :
            thread = threading.Thread(target=target_function, args=args, name=args[0])
            thread.start()               
        else:
            pass

        return None
    return inner


def new_thread(target_function):

    def inner(*args, **kwargs):

        thread = threading.Thread(target=target_function, args=args)
        thread.start()

    return inner