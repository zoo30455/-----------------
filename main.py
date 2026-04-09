from generator import generate_password
import interface
counter=0
def generate():
    interface.l_b.delete(0,"end")
    for i in range(5):
        state_lowercase=interface.lowercase.get()
        state_numbers=interface.numbers.get()
        state_simbols=interface.simbols1.get()
        state_uppercase=interface.uppercase.get()
        interface.l_b.insert("end",generate_password(state_lowercase,state_numbers,state_uppercase,state_simbols))
interface.button.config(command=generate)
interface.window.mainloop()