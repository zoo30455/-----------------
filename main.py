import generator
import interface
from tkinter import messagebox
counter=0
def generate():
    interface.l_b.delete(0,"end")
    for i in range(5):
        state_lowercase=interface.lowercase.get()
        state_numbers=interface.numbers.get()
        state_simbols=interface.simbols1.get()
        state_uppercase=interface.uppercase.get()
        try:
            generator.a=int(interface.en1.get())
            generator.b=int(interface.en2.get())
            generator.c=int(interface.en3.get())
            generator.d=int(interface.en4.get())
        except ValueError:
            messagebox.showerror("Ошибка","Введите числа")
        interface.l_b.insert("end",generator.generate_password(state_lowercase,state_numbers,state_uppercase,state_simbols))
interface.button.config(command=generate)
interface.window.mainloop()