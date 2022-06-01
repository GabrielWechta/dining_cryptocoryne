class Client:
    def run(self):
        print("Client is listening...")
        while True:
            x = input()
            print(f"You said {x}.")
            if x == "exit":
                break
