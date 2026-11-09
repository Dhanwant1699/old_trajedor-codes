ui_path = r"trajedor/ui/index.html"
with open(ui_path, "r", encoding="utf-8") as f:
    content = f.read()

target = """        function syncCortexAccounts(accounts) {"""

repl = """        const KNOWN_ACCOUNT_INFO = {
            '52053251': { trader: 'amar vijay patil', server: 'GTCGlobalSA-Server 2', broker: 'GTC Global SA (Pty) Ltd' },
            '8065799': { trader: 'AMOL AMBADAS TAWADE', server: 'ICMarketsSC-MT5-3', broker: 'IC Markets (Raw Trading Ltd)' }
        };

        function resolveAccountMeta(accId, accData) {
            if (!accData) return { server: 'MT5 Server', trader: 'ACCOUNT HOLDER', broker: 'Broker', login: 'N/A' };
            const login = accData.login ? String(accData.login) : '';
            const known = KNOWN_ACCOUNT_INFO[login] || {};
            
            let serv = accData.server || known.server || accData.name || accId;
            let trader = accData.trader_name || known.trader || 'ACCOUNT HOLDER';
            let broker = accData.broker || known.broker || accData.company || serv;

            if (serv.includes('GTC') && !broker.includes('GTC')) {
                broker = 'GTC Global SA (Pty) Ltd';
            } else if (serv.includes('ICMarkets') && !broker.includes('IC Markets')) {
                broker = 'IC Markets (Raw Trading Ltd)';
            }
            if (login === '52053251' && (!trader || trader === 'ACCOUNT HOLDER' || trader.toLowerCase() === 'trader')) {
                trader = 'amar vijay patil';
            }
            if (login === '8065799' && (!trader || trader === 'ACCOUNT HOLDER' || trader.toLowerCase() === 'trader')) {
                trader = 'AMOL AMBADAS TAWADE';
            }

            return { server: serv, trader: trader, broker: broker, login: login };
        }

        function syncCortexAccounts(accounts) {"""

assert target in content, "target syncCortexAccounts not found"
content = content.replace(target, repl, 1)

# Update syncCortexAccounts body to use resolveAccountMeta
target_cortex_body = """                const serv = a.server || a.name || accId;
                const trader = a.trader_name || 'TRADER';
                const login = (a.login && a.login !== 0) ? a.login : 'LIVE';"""

repl_cortex_body = """                const meta = resolveAccountMeta(accId, a);
                const serv = meta.server;
                const trader = meta.trader;
                const broker = meta.broker;
                const login = meta.login || 'LIVE';"""

assert target_cortex_body in content, "target_cortex_body not found"
content = content.replace(target_cortex_body, repl_cortex_body, 1)

# Update syncFleetAccounts to use resolveAccountMeta
target_fleet_body = """                    const serverName = accData.server || accData.name || `Terminal ${accId}`;
                    const brokerName = accData.broker || accData.company || serverName;
                    const traderName = accData.trader_name || 'ACCOUNT HOLDER';"""

repl_fleet_body = """                    const meta = resolveAccountMeta(accId, accData);
                    const serverName = meta.server;
                    const brokerName = meta.broker;
                    const traderName = meta.trader;"""

assert target_fleet_body in content, "target_fleet_body not found"
content = content.replace(target_fleet_body, repl_fleet_body, 1)

# Update updateAccountMeter to use resolveAccountMeta
target_meter_dyn = """            // Dynamically refresh trader name, server, broker, login, and status
            const holderEl = document.getElementById(`v-holder-${accId}`);
            if (holderEl && accData.trader_name) holderEl.innerText = accData.trader_name.toUpperCase();

            const servEl = document.getElementById(`v-server-${accId}`);
            if (servEl && (accData.server || accData.name)) servEl.innerText = accData.server || accData.name;

            const brokEl = document.getElementById(`v-broker-${accId}`);
            if (brokEl && accData.broker) brokEl.innerText = accData.broker;

            const loginEl = document.getElementById(`v-login-${accId}`);
            if (loginEl && accData.login) loginEl.innerText = `#${accData.login}`;"""

repl_meter_dyn = """            // Dynamically refresh trader name, server, broker, login, and status
            const meta = resolveAccountMeta(accId, accData);
            const holderEl = document.getElementById(`v-holder-${accId}`);
            if (holderEl && meta.trader) holderEl.innerText = meta.trader.toUpperCase();

            const servEl = document.getElementById(`v-server-${accId}`);
            if (servEl && meta.server) servEl.innerText = meta.server;

            const brokEl = document.getElementById(`v-broker-${accId}`);
            if (brokEl && meta.broker) brokEl.innerText = meta.broker;

            const loginEl = document.getElementById(`v-login-${accId}`);
            if (loginEl && meta.login) loginEl.innerText = `#${meta.login}`;"""

assert target_meter_dyn in content, "target_meter_dyn not found"
content = content.replace(target_meter_dyn, repl_meter_dyn, 1)

with open(ui_path, "w", encoding="utf-8") as f:
    f.write(content)
print("SUCCESSFULLY_UPDATED_RESOLVER")
