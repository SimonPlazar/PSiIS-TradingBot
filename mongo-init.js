db = db.getSiblingDB('trading_bot');

db.createUser({
    user: "admin",
    pwd: "adminpass",
    roles: [{role: "readWrite", db: "trading_bot"}]
});

db.currencies.insertMany([
    {symbol: "EUR", balance: 10000},
    {symbol: "BTC", balance: 0.5},
    {symbol: "ETH", balance: 5}
]);

db.transactions.createIndex({timestamp: -1});