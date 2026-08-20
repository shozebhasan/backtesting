import MetaTrader5 as mt5


def main():
    if not mt5.initialize():
        print("❌ Could not connect to MT5")
        print("Error:", mt5.last_error())
        return

    print("✅ Connected to MT5")

    print("\nMT5 version:")
    print(mt5.version())

    print("\nTerminal:")
    print(mt5.terminal_info())

    print("\nAccount:")
    account = mt5.account_info()

    if account is None:
        print("No trading account currently logged in.")
    else:
        print("Login:", account.login)
        print("Server:", account.server)
        print("Currency:", account.currency)
        print("Balance:", account.balance)

    mt5.shutdown()


if __name__ == "__main__":
    main()