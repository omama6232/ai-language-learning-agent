"""
Conversational English Practice Bot - CLI entry point
Run: python main.py
"""

from agent import LanguageAgent

def main():
    print("=" * 50)
    print("English Practice Bot")
    print("Type a sentence in English. Type 'exit' to quit.")
    print("Type 'progress' to see your stats.")
    print("=" * 50)

    agent = LanguageAgent()

    while True:
        user_input = input("\nYou: ").strip()

        if user_input.lower() == "exit":
            print("Bot: Goodbye! Keep practicing.")
            agent.show_progress()
            break

        if user_input.lower() == "progress":
            agent.show_progress()
            continue

        if not user_input:
            continue

        response = agent.process_message(user_input)
        print(f"Bot: {response}")


if __name__ == "__main__":
    main()
