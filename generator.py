import random
a=4
b=4
c=4
d=4
def generate_password(lowercase,numbers,uppercase,simbols1):
    password=[]
    abc="abcdefghijklmnopqrstuvwxyz"
    a_b_c="ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if lowercase==True:
        for i in range(a):
            password.append(random.choice(abc))
    if numbers==True:
        for i in range(b):
            password.append(random.choice("0123456789"))
    if uppercase==True:
        for i in range(c):
            password.append(random.choice(a_b_c))
    if simbols1==True:
        for i in range(d):
            password.append(random.choice("!@#$%^&*()"))
    random.shuffle(password)
    password="".join(password)
    return password