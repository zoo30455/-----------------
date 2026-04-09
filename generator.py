import random
def generate_password(lowercase,numbers,uppercase,simbols1):
    password=[]
    abc="abcdefghijklmnopqrstuvwxyz"
    a_b_c="ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if lowercase==True:
        for i in range(4):
            password.append(random.choice(abc))
    if numbers==True:
        for i in range(4):
            password.append(random.choice("0123456789"))
    if uppercase==True:
        for i in range(2):
            password.append(random.choice(a_b_c))
    if simbols1==True:
        for i in range(3):
            password.append(random.choice("!@#$%^&*()"))
    random.shuffle(password)
    password="".join(password)
    password=(f"   {password}")
    return password