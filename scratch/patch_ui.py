import re

ui_path = r"trajedor/ui/index.html"
with open(ui_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update syncCortexAccounts
old_cortex = """        function syncCortexAccounts(accounts) {
            const strip = document.getElementById('cortex-accounts-strip');
            if (!strip) return;
            const accIds = Object.keys(accounts || {});
            const badge = document.getElementById('cortex-fleet-badge');
            if (badge) badge.innerText = `${accIds.length} ACTIVE TERMINALS`;

            if (accIds.length === 0) {
                strip.innerHTML = '<div style="color: #64748b; font-size: 11px;">No active terminals detected on PC.</div>';
                return;
            }
            strip.innerHTML = accIds.map(accId => {
                const a = accounts[accId] || {};
                const curr = a.currency || 'USD';
                const currSymbol = curr === 'EUR' ? '€' : '$';
                const eq = a.equity !== undefined ? `${currSymbol}${Number(a.equity).toFixed(2)}` : '0.00';
                return `
                <div style="background: rgba(2, 6, 23, 0.6); padding: 8px 12px; border-radius: 8px; border: 1px solid rgba(56, 189, 248, 0.2);">
                    <div style="color: #94a3af; font-size: 10px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${a.name || accId}</div>
                    <div style="color: var(--neural-emerald); font-weight: 700; font-size: 13px;">${eq}</div>
                    <div style="color: #64748b; font-size: 9px; font-family: var(--font-mono);">Login: ${a.login || 'N/A'} • ${a.status || 'CONNECTED'}</div>
                </div>`;
            }).join('');
        }"""

new_cortex = """        function syncCortexAccounts(accounts) {
            const strip = document.getElementById('cortex-accounts-strip');
            if (!strip) return;
            const accIds = Object.keys(accounts || {});
            const badge = document.getElementById('cortex-fleet-badge');
            if (badge) badge.innerText = `${accIds.length} ACTIVE TERMINALS`;

            if (accIds.length === 0) {
                strip.innerHTML = '<div style="color: #64748b; font-size: 11px;">No active terminals detected on PC.</div>';
                return;
            }
            strip.innerHTML = accIds.map(accId => {
                const a = accounts[accId] || {};
                const curr = a.currency || 'USD';
                const currSymbol = curr === 'EUR' ? '€' : '$';
                const eq = a.equity !== undefined ? `${currSymbol}${Number(a.equity).toFixed(2)}` : '0.00';
                const serv = a.server || a.name || accId;
                const trader = a.trader_name || 'TRADER';
                const login = (a.login && a.login !== 0) ? a.login : 'LIVE';
                return `
                <div style="background: rgba(2, 6, 23, 0.6); padding: 8px 12px; border-radius: 8px; border: 1px solid rgba(56, 189, 248, 0.2); min-width: 175px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; gap: 8px;">
                        <span style="color: #fff; font-weight: 700; font-size: 11px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${serv}</span>
                        <span style="color: var(--neural-cyan); font-size: 10px; font-family: var(--font-mono); font-weight: 700;">#${login}</span>
                    </div>
                    <div style="color: #38bdf8; font-size: 10px; font-weight: 600; margin-top: 3px; text-transform: uppercase; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">👤 ${trader}</div>
                    <div style="color: var(--neural-emerald); font-weight: 700; font-size: 13px; margin-top: 4px;">${eq}</div>
                    <div style="color: #64748b; font-size: 9px; font-family: var(--font-mono);">${a.broker || serv} &bull; ${a.status || 'CONNECTED'}</div>
                </div>`;
            }).join('');
        }"""

assert old_cortex in content, "old_cortex not found"
content = content.replace(old_cortex, new_cortex, 1)

# 2. Update syncFleetAccounts
old_fleet_start = """            // For each account, if its card doesn't exist yet, render it dynamically
            accIds.forEach(accId => {
                let card = document.getElementById(`acc-card-${accId}`);
                if (!card) {
                    const accData = accounts[accId];
                    const num = accId.replace('acc_', '');
                    const curr = accData.currency || 'USD';
                    const currSymbol = curr === 'EUR' ? '€' : '$';
                    const magic = accData.magic_number || (888990 + (parseInt(num) || 1));
                    const isConn = (accData.status || 'CONNECTED') === 'CONNECTED';
                    const statusStr = accData.status || (isConn ? 'CONNECTED' : 'OFFLINE');
                    const statusColor = isConn ? 'var(--neural-emerald)' : (statusStr === 'DISARMED' ? 'var(--neural-gold)' : '#f43f5e');
                    const login = (accData.login && accData.login !== 0) ? accData.login : (isConn ? 'LIVE' : 'OFFLINE');
                    const accName = accData.name || `Terminal ${accId}`;

                    const cardHtml = `
                    <div class="account-control-card" id="acc-card-${accId}">
                        <div>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                                <div style="font-family: var(--font-display); font-size: 14px; font-weight: 700; color: #fff;">${accName}</div>
                                <button class="power-toggle-btn" id="pwr-${accId}" onclick="toggleAccountPower('${accId}')" title="Toggle Trajedor trading on this account">
                                    <svg viewBox="0 0 24 24" class="pwr-icon"><path d="M13 3h-2v10h2V3zm4.83 2.17l-1.42 1.42C17.99 7.86 19 9.81 19 12c0 3.87-3.13 7-7 7s-7-3.13-7-7c0-2.19 1.01-4.14 2.58-5.42L6.17 5.17C4.23 6.82 3 9.26 3 12c0 4.97 4.03 9 9 9s9-4.03 9-9c0-2.74-1.23-5.18-3.17-6.83z"/></svg>
                                    <span class="pwr-label" id="pwr-label-${accId}">ARMED</span>
                                </button>
                            </div>
                            <div style="font-size: 11px; color: #64748b; margin-bottom: 8px;">
                                <span style="color: ${statusColor}; font-weight: 700;">● ${statusStr}</span> &bull; ${curr} &bull; Login #${login} &bull; Magic: ${magic}
                            </div>"""

new_fleet_start = """            // For each account, if its card doesn't exist yet, render it dynamically
            accIds.forEach(accId => {
                let card = document.getElementById(`acc-card-${accId}`);
                if (!card) {
                    const accData = accounts[accId];
                    const num = accId.replace('acc_', '');
                    const curr = accData.currency || 'USD';
                    const currSymbol = curr === 'EUR' ? '€' : '$';
                    const magic = accData.magic_number || (888990 + (parseInt(num) || 1));
                    const isConn = (accData.status || 'CONNECTED') === 'CONNECTED';
                    const statusStr = accData.status || (isConn ? 'CONNECTED' : 'OFFLINE');
                    const statusColor = isConn ? 'var(--neural-emerald)' : (statusStr === 'DISARMED' ? 'var(--neural-gold)' : '#f43f5e');
                    const login = (accData.login && accData.login !== 0) ? accData.login : (isConn ? 'LIVE' : 'OFFLINE');
                    const serverName = accData.server || accData.name || `Terminal ${accId}`;
                    const brokerName = accData.broker || accData.company || serverName;
                    const traderName = accData.trader_name || 'ACCOUNT HOLDER';

                    const cardHtml = `
                    <div class="account-control-card" id="acc-card-${accId}">
                        <div>
                            <!-- Server & Power Button Row -->
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; gap: 8px;">
                                <div>
                                    <div style="font-family: var(--font-display); font-size: 15px; font-weight: 800; color: #fff; letter-spacing: 0.5px; display: flex; align-items: center; gap: 6px;">
                                        <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: ${statusColor}; box-shadow: 0 0 8px ${statusColor};" id="v-dot-${accId}"></span>
                                        <span id="v-server-${accId}">${serverName}</span>
                                    </div>
                                    <div style="font-size: 11px; color: #94a3af; margin-top: 2px;" id="v-broker-${accId}">
                                        ${brokerName}
                                    </div>
                                </div>
                                <button class="power-toggle-btn" id="pwr-${accId}" onclick="toggleAccountPower('${accId}')" title="Toggle Trajedor trading on this account">
                                    <svg viewBox="0 0 24 24" class="pwr-icon"><path d="M13 3h-2v10h2V3zm4.83 2.17l-1.42 1.42C17.99 7.86 19 9.81 19 12c0 3.87-3.13 7-7 7s-7-3.13-7-7c0-2.19 1.01-4.14 2.58-5.42L6.17 5.17C4.23 6.82 3 9.26 3 12c0 4.97 4.03 9 9 9s9-4.03 9-9c0-2.74-1.23-5.18-3.17-6.83z"/></svg>
                                    <span class="pwr-label" id="pwr-label-${accId}">ARMED</span>
                                </button>
                            </div>

                            <!-- Account Holder & Account Number Badge Row -->
                            <div style="display: flex; align-items: center; justify-content: space-between; background: rgba(15, 23, 42, 0.6); padding: 8px 12px; border-radius: 8px; border: 1px solid rgba(56, 189, 248, 0.2); margin-bottom: 10px;">
                                <div style="display: flex; align-items: center; gap: 8px;">
                                    <span style="font-size: 16px;">👤</span>
                                    <div>
                                        <div style="font-size: 12px; font-weight: 700; color: #f8fafc; text-transform: uppercase;" id="v-holder-${accId}">
                                            ${traderName}
                                        </div>
                                        <div style="font-size: 10px; color: #64748b; font-family: var(--font-mono);">
                                            ACCOUNT HOLDER
                                        </div>
                                    </div>
                                </div>
                                <div style="text-align: right;">
                                    <div style="font-family: var(--font-mono); font-size: 13px; font-weight: 700; color: var(--neural-cyan);" id="v-login-${accId}">
                                        #${login}
                                    </div>
                                    <div style="font-size: 9px; color: #64748b; font-family: var(--font-mono);">
                                        MAGIC: ${magic} &bull; ${curr}
                                    </div>
                                </div>
                            </div>

                            <!-- Connection Status Pill -->
                            <div style="display: flex; align-items: center; gap: 8px; font-size: 11px; margin-bottom: 10px; color: #64748b;">
                                <span style="color: ${statusColor}; font-weight: 700;" id="v-status-${accId}">● ${statusStr}</span>
                                <span>&bull;</span>
                                <span style="color: #94a3af;">Execution Bridge Ready</span>
                            </div>"""

assert old_fleet_start in content, "old_fleet_start not found"
content = content.replace(old_fleet_start, new_fleet_start, 1)

# 3. Update the save button inside the card template
old_btn = """                        <button class="btn-save-limits" id="btn-save-${accId}" onclick="saveAccountLimits('${accId}')">
                            <span>⚡ SAVE ${accName.split(' ')[0].toUpperCase()} LIMITS</span>
                        </button>"""

new_btn = """                        <button class="btn-save-limits" id="btn-save-${accId}" onclick="saveAccountLimits('${accId}')">
                            <span>⚡ SAVE ${serverName.split(' ')[0].toUpperCase()} LIMITS</span>
                        </button>"""

assert old_btn in content, "old_btn not found"
content = content.replace(old_btn, new_btn, 1)

# 4. Update updateAccountMeter to dynamically refresh trader_name, server, broker, login, status
old_meter_header = """            const bEl = document.getElementById(`v-b-${accId}`) || document.getElementById(`v-b${num}`);
            const eEl = document.getElementById(`v-e-${accId}`) || document.getElementById(`v-e${num}`);
            if (bEl && accData.balance !== undefined) bEl.innerText = `${currSymbol}${Number(accData.balance).toFixed(2)}`;
            if (eEl && accData.equity !== undefined) eEl.innerText = `${currSymbol}${Number(accData.equity).toFixed(2)}`;"""

new_meter_header = """            const bEl = document.getElementById(`v-b-${accId}`) || document.getElementById(`v-b${num}`);
            const eEl = document.getElementById(`v-e-${accId}`) || document.getElementById(`v-e${num}`);
            if (bEl && accData.balance !== undefined) bEl.innerText = `${currSymbol}${Number(accData.balance).toFixed(2)}`;
            if (eEl && accData.equity !== undefined) eEl.innerText = `${currSymbol}${Number(accData.equity).toFixed(2)}`;

            // Dynamically refresh trader name, server, broker, login, and status
            const holderEl = document.getElementById(`v-holder-${accId}`);
            if (holderEl && accData.trader_name) holderEl.innerText = accData.trader_name.toUpperCase();

            const servEl = document.getElementById(`v-server-${accId}`);
            if (servEl && (accData.server || accData.name)) servEl.innerText = accData.server || accData.name;

            const brokEl = document.getElementById(`v-broker-${accId}`);
            if (brokEl && accData.broker) brokEl.innerText = accData.broker;

            const loginEl = document.getElementById(`v-login-${accId}`);
            if (loginEl && accData.login) loginEl.innerText = `#${accData.login}`;

            const statusEl = document.getElementById(`v-status-${accId}`);
            const dotEl = document.getElementById(`v-dot-${accId}`);
            const isConn = (accData.status || 'CONNECTED') === 'CONNECTED';
            const statusStr = accData.status || (isConn ? 'CONNECTED' : 'OFFLINE');
            const statusColor = isConn ? 'var(--neural-emerald)' : (statusStr === 'DISARMED' ? 'var(--neural-gold)' : '#f43f5e');
            if (statusEl) {
                statusEl.innerText = `● ${statusStr}`;
                statusEl.style.color = statusColor;
            }
            if (dotEl) {
                dotEl.style.background = statusColor;
                dotEl.style.boxShadow = `0 0 8px ${statusColor}`;
            }"""

assert old_meter_header in content, "old_meter_header not found"
content = content.replace(old_meter_header, new_meter_header, 1)

with open(ui_path, "w", encoding="utf-8") as f:
    f.write(content)
print("SUCCESSFULLY_PATCHED_UI")
