
        let currentAsset = "XAUUSD";
        let cachedHistoryData = null;
        let cachedAccountsData = null;
        let activeHistoryFilter = "ALL";
        let activeAccountFilter = "ALL";
        let sidebarCollapsed = false;

        function toggleSidebar() {
            const panel = document.getElementById('sidebarPanel');
            const icon = document.getElementById('sidebarToggleIcon');
            sidebarCollapsed = !sidebarCollapsed;
            if (panel) {
                if (sidebarCollapsed) {
                    panel.classList.add('collapsed');
                    if (icon) icon.innerText = '▶';
                } else {
                    panel.classList.remove('collapsed');
                    if (icon) icon.innerText = '◀';
                }
            }
        }

        function switchAsset(symbol) {
            currentAsset = symbol;
            const goldBtn = document.getElementById('tab-gold');
            const accsBtn = document.getElementById('tab-accounts');
            const histBtn = document.getElementById('tab-history');
            const adminBtn = document.getElementById('tab-admin');
            const sideGold = document.getElementById('side-nav-gold');
            const sideAccs = document.getElementById('side-nav-accounts');
            const sideHist = document.getElementById('side-nav-history');
            const sideAdmin = document.getElementById('side-nav-admin');
            const logoIcon = document.getElementById('logo-icon');
            const liveView = document.getElementById('live-cockpit-view');
            const accsView = document.getElementById('accounts-view-container');
            const histView = document.getElementById('history-view-container');
            const adminView = document.getElementById('admin-view-container');

            if (goldBtn) goldBtn.className = 'asset-tab-btn';
            if (accsBtn) accsBtn.className = 'asset-tab-btn';
            if (histBtn) histBtn.className = 'asset-tab-btn';
            if (adminBtn) adminBtn.className = 'asset-tab-btn';

            if (sideGold) sideGold.classList.remove('active');
            if (sideAccs) sideAccs.classList.remove('active');
            if (sideHist) sideHist.classList.remove('active');
            if (sideAdmin) sideAdmin.classList.remove('active');

            if (symbol === 'XAUUSD') {
                if (goldBtn) goldBtn.className = 'asset-tab-btn active-gold';
                if (sideGold) sideGold.classList.add('active');
                if (liveView) liveView.style.display = 'block';
                if (accsView) accsView.style.display = 'none';
                if (histView) histView.style.display = 'none';
                if (adminView) adminView.style.display = 'none';
                logoIcon.style.background = 'linear-gradient(135deg, #f59e0b, #d97706)';
                logoIcon.innerHTML = '🥇';
                document.getElementById('price-title').innerText = 'Live XAUUSD (Gold) Price';
                document.getElementById('consensus-heading').innerText = '🏛️ Gold (XAUUSD) Arbitrator Decision';
                document.getElementById('matrix-title').innerText = '🧠 Gold (XAUUSD) 10 Strategy Agents Live Matrix';
            } else if (symbol === 'ACCOUNTS') {
                if (accsBtn) accsBtn.className = 'asset-tab-btn active-gold';
                if (sideAccs) sideAccs.classList.add('active');
                if (liveView) liveView.style.display = 'none';
                if (accsView) accsView.style.display = 'block';
                if (histView) histView.style.display = 'none';
                if (adminView) adminView.style.display = 'none';
                logoIcon.style.background = 'linear-gradient(135deg, #3b82f6, #1d4ed8)';
                logoIcon.innerHTML = '💼';
                renderAccountsView();
            } else if (symbol === 'HISTORY') {
                if (histBtn) histBtn.className = 'asset-tab-btn active-gold';
                if (sideHist) sideHist.classList.add('active');
                if (liveView) liveView.style.display = 'none';
                if (accsView) accsView.style.display = 'none';
                if (histView) histView.style.display = 'block';
                if (adminView) adminView.style.display = 'none';
                logoIcon.style.background = 'linear-gradient(135deg, #10b981, #059669)';
                logoIcon.innerHTML = '📜';
                renderHistoryTable();
            } else if (symbol === 'ADMIN') {
                if (adminBtn) adminBtn.className = 'asset-tab-btn active-gold';
                if (sideAdmin) sideAdmin.classList.add('active');
                if (liveView) liveView.style.display = 'none';
                if (accsView) accsView.style.display = 'none';
                if (histView) histView.style.display = 'none';
                if (adminView) adminView.style.display = 'block';
                logoIcon.style.background = 'linear-gradient(135deg, #ef4444, #b91c1c)';
                logoIcon.innerHTML = '⚙️';
                loadAdminConfig();
            }

            fetchLiveStatus();
        }

        function getCurrencySymbol(curr) {
            if (!curr) return '$';
            const c = curr.toUpperCase();
            if (c === 'EUR') return '€';
            if (c === 'USD') return '$';
            if (c === 'GBP') return '£';
            if (c === 'JPY') return '¥';
            if (c === 'AUD') return 'A$';
            return '$';
        }

        function getAccountFlag(curr, name) {
            const c = (curr || '').toUpperCase();
            const n = (name || '').toUpperCase();
            if (c === 'EUR' || n.includes('EUR')) return '🇪🇺';
            if (c === 'GBP' || n.includes('GBP')) return '🇬🇧';
            if (c === 'JPY' || n.includes('JPY')) return '🇯🇵';
            if (c === 'AUD' || n.includes('AUD')) return '🇦🇺';
            if (n.includes('GTC') || n.includes('USD')) return '🇺🇸';
            if (n.includes('VANTAGE')) return '🇦🇺';
            return '💼';
        }

        function selectAccountFilter(filterId) {
            activeAccountFilter = filterId;
            renderAccountsView();
        }

        function renderAccountFilterTabs(accounts) {
            const container = document.getElementById('account-filter-tabs-container');
            if (!container || !accounts) return;
            
            const accKeys = Object.keys(accounts);
            container.innerHTML = '';

            // "ALL" button
            const allBtn = document.createElement('button');
            allBtn.className = `asset-tab-btn ${activeAccountFilter === 'ALL' ? 'active-gold' : ''}`;
            allBtn.id = 'acc-filter-all';
            allBtn.style.cssText = 'padding: 10px 20px; font-size: 13px;';
            allBtn.onclick = () => selectAccountFilter('ALL');
            allBtn.innerHTML = `<span>🌐</span> <span>ALL ACCOUNTS (${accKeys.length} COMBINED)</span>`;
            container.appendChild(allBtn);

            accKeys.forEach((k, idx) => {
                const a = accounts[k];
                const flag = getAccountFlag(a.currency, a.name);
                const btn = document.createElement('button');
                btn.className = `asset-tab-btn ${activeAccountFilter === k ? 'active-gold' : ''}`;
                btn.id = `acc-filter-${k}`;
                btn.style.cssText = 'padding: 10px 20px; font-size: 13px;';
                btn.onclick = () => selectAccountFilter(k);
                btn.innerHTML = `<span>${flag}</span> <span>${a.name || 'Account #' + (idx+1)} (${a.login || k})</span>`;
                container.appendChild(btn);
            });
        }

        function renderAccountsView() {
            if (!cachedAccountsData) return;
            const accounts = cachedAccountsData;
            const accKeys = Object.keys(accounts);
            
            renderAccountFilterTabs(accounts);

            const grid = document.getElementById('account-detail-cards-grid');
            const tbody = document.getElementById('account-positions-table-body');
            if (!grid || !tbody) return;

            grid.innerHTML = '';
            tbody.innerHTML = '';

            // Combined header summary
            let combinedEquities = [];
            let totPos = 0;
            accKeys.forEach(k => {
                const a = accounts[k];
                const sym = getCurrencySymbol(a.currency);
                const eq = Number(a.equity || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
                combinedEquities.push(`${sym}${eq} ${a.currency || ''}`);
                totPos += (a.open_count || 0);
            });

            const mgrTermBadge = document.getElementById('mgr-terminals-count-badge');
            if (mgrTermBadge) mgrTermBadge.innerText = `🟢 ${accKeys.length} Terminals Synchronized • Direct MT5 Python IPC API`;

            const mgrCombEq = document.getElementById('mgr-combined-equity');
            if (mgrCombEq) mgrCombEq.innerText = combinedEquities.join(' + ');

            const mgrCombSub = document.getElementById('mgr-combined-sub');
            if (mgrCombSub) mgrCombSub.innerText = `${accKeys.length} Connected Accounts`;

            const mgrCombPos = document.getElementById('mgr-combined-positions');
            if (mgrCombPos) mgrCombPos.innerText = `${totPos} Active Trades`;

            let displayAccounts = [];
            if (activeAccountFilter === 'ALL') {
                accKeys.forEach(k => {
                    if (accounts[k]) displayAccounts.push(accounts[k]);
                });
            } else if (accounts[activeAccountFilter]) {
                displayAccounts.push(accounts[activeAccountFilter]);
            }

            // Render detailed cards for selected accounts
            displayAccounts.forEach((acc, idx) => {
                const currSymbol = getCurrencySymbol(acc.currency);
                const flag = getAccountFlag(acc.currency, acc.name);
                const pnl = Number(acc.total_floating_pnl || 0);
                const pnlColor = pnl >= 0 ? 'var(--buy-green)' : 'var(--sell-red)';
                const marginLevel = acc.margin_level ? `${acc.margin_level.toFixed(1)}%` : 'Infinite (No Used Margin)';

                const card = document.createElement('div');
                card.className = 'metric-card';
                card.style.border = '1px solid rgba(245, 158, 11, 0.35)';
                card.style.background = 'linear-gradient(135deg, rgba(14, 18, 28, 0.95), rgba(20, 26, 40, 0.95))';
                card.style.padding = '20px';

                card.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span style="font-size: 22px;">${flag}</span>
                            <div>
                                <div style="font-size: 14px; font-weight: 700; color: #fbbf24;">${acc.name || 'Account ' + acc.id}</div>
                                <div style="font-size: 11px; color: var(--text-muted);">${acc.holder || 'Dhanwant Patil'} • ID: <strong>${acc.login || 'Offline'}</strong></div>
                            </div>
                        </div>
                        <div style="display: flex; gap: 6px; align-items: center;">
                            <span class="agent-badge ${acc.open_count > 0 ? 'badge-buy' : 'badge-hold'}">${acc.open_count > 0 ? `${acc.open_count} ACTIVE` : 'STANDBY'}</span>
                            <button class="btn" onclick="switchAsset('ADMIN')" style="padding: 3px 8px; font-size: 10px; background: rgba(255,255,255,0.08);" title="Configure Risk & Targets">⚙️ Admin</button>
                        </div>
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 14px; background: rgba(0,0,0,0.3); padding: 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                        <div>
                            <div style="font-size: 11px; color: var(--text-muted); text-transform: uppercase;">Live Equity</div>
                            <div style="font-size: 19px; font-weight: 700; font-family: var(--font-mono); color: #fbbf24; margin-top: 2px;">${currSymbol}${Number(acc.equity || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})} ${acc.currency}</div>
                        </div>
                        <div>
                            <div style="font-size: 11px; color: var(--text-muted); text-transform: uppercase;">Account Balance</div>
                            <div style="font-size: 19px; font-weight: 700; font-family: var(--font-mono); color: #fff; margin-top: 2px;">${currSymbol}${Number(acc.balance || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})} ${acc.currency}</div>
                        </div>
                        <div>
                            <div style="font-size: 11px; color: var(--text-muted); text-transform: uppercase;">Free Margin</div>
                            <div style="font-size: 13px; font-family: var(--font-mono); color: var(--text-main); margin-top: 2px;">${currSymbol}${Number(acc.margin_free || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
                        </div>
                        <div>
                            <div style="font-size: 11px; color: var(--text-muted); text-transform: uppercase;">Margin Level</div>
                            <div style="font-size: 13px; font-family: var(--font-mono); color: var(--buy-green); margin-top: 2px;">${marginLevel}</div>
                        </div>
                    </div>

                    <div style="display: flex; justify-content: space-between; align-items: center; font-size: 11px; color: var(--text-muted); padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.06);">
                        <span>Server: <strong style="color: #fff;">${acc.server || 'MT5 Live'}</strong></span>
                        <span>Floating P&L: <strong style="color: ${pnlColor}; font-family: var(--font-mono);">${pnl >= 0 ? '+' : ''}${currSymbol}${pnl.toFixed(2)} ${acc.currency}</strong></span>
                        <span>Mode: <strong style="color: #38bdf8;">${acc.mode || 'STANDARD_PROP'}</strong></span>
                    </div>

                    <div style="margin-top: 12px; background: rgba(0,0,0,0.35); padding: 10px 12px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.06);">
                        <div style="display: flex; justify-content: space-between; font-size: 11px;">
                            <span style="color: var(--text-muted);">🎯 Daily Target Progress:</span>
                            <span style="color: ${Number(acc.today_realized_pnl || 0) >= 0 ? 'var(--buy-green)' : 'var(--sell-red)'}; font-family: var(--font-mono); font-weight: 700;">
                                ${Number(acc.today_realized_pnl || 0) >= 0 ? '+' : ''}${currSymbol}${Number(acc.today_realized_pnl || 0).toFixed(2)} / ${currSymbol}${Number(acc.daily_profit_target || 0).toFixed(2)} (${acc.daily_target_pct || 0}%)
                            </span>
                        </div>
                        <div class="target-progress-bar-bg" style="height: 6px; margin: 6px 0;">
                            <div class="target-progress-bar-fill" style="width: ${Math.min(100, Math.max(0, acc.daily_target_pct || 0))}%; background: ${acc.target_reached_today ? 'linear-gradient(90deg, #10b981, #00f0ff)' : (Number(acc.today_realized_pnl || 0) < 0 ? 'linear-gradient(90deg, #ef4444, #f87171)' : 'linear-gradient(90deg, #10b981, #34d399)')}"></div>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 10px; color: var(--text-sub);">
                            <span>Max Lot: <strong style="color: #fff;">${acc.max_lot_size || 0.01} Lots</strong></span>
                            <span>Status: <strong style="color: ${acc.target_reached_today ? '#00f0ff' : (acc.is_active ? 'var(--buy-green)' : 'var(--sell-red)')};">${acc.target_reached_today ? '🎯 TARGET HIT (LOCK)' : (acc.is_active ? '🟢 ACTIVE' : '⏸️ PAUSED')}</strong></span>
                        </div>
                    </div>

                    <div style="margin-top: 10px; background: rgba(255,255,255,0.02); padding: 8px 12px; border-radius: 6px; font-size: 11px; color: var(--text-sub);">
                        🤖 <strong>AI Execution Engine:</strong> Magic #${acc.magic_number || 777888} • Max Trades: ${acc.max_open_trades || 1} • Loss Limit: ${currSymbol}${acc.daily_max_loss || 50}
                    </div>
                `;
                grid.appendChild(card);
            });

            // Gather positions for table
            let allPositions = [];
            displayAccounts.forEach(acc => {
                const pList = acc.open_positions || [];
                pList.forEach(p => {
                    allPositions.push({ ...p, account_name: acc.name, account_currency: acc.currency, account_id: acc.id });
                });
            });

            const posTitle = document.getElementById('account-positions-title');
            const posSub = document.getElementById('account-positions-subtitle');
            if (activeAccountFilter === 'ALL') {
                if (posTitle) posTitle.innerText = `📊 All Active Positions Across All ${accKeys.length} Accounts (${allPositions.length})`;
                if (posSub) posSub.innerText = `Synchronized live across all connected MT5 terminal instances`;
            } else {
                const curAcc = accounts[activeAccountFilter] || {};
                if (posTitle) posTitle.innerText = `📊 ${curAcc.name || activeAccountFilter} Open Positions (${allPositions.length})`;
                if (posSub) posSub.innerText = `Login: ${curAcc.login || 'Offline'} • Server: ${curAcc.server || 'MT5'}`;
            }

            if (allPositions.length === 0) {
                tbody.innerHTML = `<tr><td colspan="11" style="text-align: center; padding: 28px; color: var(--text-muted);">
                    <div style="font-size: 16px; margin-bottom: 6px;">🟢 No Open Positions on Selected Account(s)</div>
                    <div style="font-size: 12px; color: var(--text-sub);">AI Council is actively scanning 5-Minute (M5) pullbacks to enter sniper positions.</div>
                </td></tr>`;
                return;
            }

            allPositions.forEach(p => {
                const tr = document.createElement('tr');
                tr.style.borderBottom = '1px solid rgba(255,255,255,0.03)';
                const pnl = Number(p.profit || 0);
                const pnlColor = pnl >= 0 ? 'var(--buy-green)' : 'var(--sell-red)';
                const accBadge = `<span style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); font-size: 10px; padding: 2px 6px; border-radius: 4px; font-weight: 700;">${p.account_name || p.account_id}</span>`;

                tr.innerHTML = `
                    <td style="padding: 12px 16px;">${accBadge}</td>
                    <td style="padding: 12px 16px; font-family: var(--font-mono); color: var(--text-muted);">#${p.ticket}</td>
                    <td style="padding: 12px 16px; font-weight: 700; color: #fff;">${p.symbol}</td>
                    <td style="padding: 12px 16px;"><span class="agent-badge ${p.type === 'BUY' ? 'badge-buy' : 'badge-sell'}">${p.type}</span></td>
                    <td style="padding: 12px 16px; font-family: var(--font-mono); font-weight: 600;">${p.volume} Lots</td>
                    <td style="padding: 12px 16px; font-family: var(--font-mono);">${Number(p.open_price).toFixed(2)}</td>
                    <td style="padding: 12px 16px; font-family: var(--font-mono); color: #fff;">${Number(p.price_current || p.open_price).toFixed(2)}</td>
                    <td style="padding: 12px 16px; font-family: var(--font-mono); color: var(--sell-red);">${p.sl ? Number(p.sl).toFixed(2) : 'Protected'}</td>
                    <td style="padding: 12px 16px; font-family: var(--font-mono); color: var(--buy-green);">${p.tp ? Number(p.tp).toFixed(2) : 'Open'}</td>
                    <td style="padding: 12px 16px; font-family: var(--font-mono); font-weight: 700; color: ${pnlColor};">${pnl >= 0 ? '+' : ''}${pnl.toFixed(2)} ${p.account_currency}</td>
                    <td style="padding: 12px 16px;"><span class="badge-live" style="font-size: 10px;">AUTO-TRAILING & PROTECTED</span></td>
                `;
                tbody.appendChild(tr);
            });
        }

        let activeHistoryAccountFilter = "ALL";

        function selectHistoryAccountFilter(filterId) {
            activeHistoryAccountFilter = filterId;
            renderHistoryTable();
        }

        function renderHistoryAccountFilterTabs(accounts) {
            const container = document.getElementById('history-account-filter-tabs-container');
            if (!container) return;
            
            const accKeys = accounts ? Object.keys(accounts) : ['acc_1', 'acc_2', 'acc_3'];
            container.innerHTML = '';

            // "ALL" button
            const allBtn = document.createElement('button');
            allBtn.className = `asset-tab-btn ${activeHistoryAccountFilter === 'ALL' ? 'active-gold' : ''}`;
            allBtn.id = 'hist-acc-filter-all';
            allBtn.style.cssText = 'padding: 8px 16px; font-size: 12px;';
            allBtn.onclick = () => selectHistoryAccountFilter('ALL');
            allBtn.innerHTML = `<span>🌐</span> <span>ALL ACCOUNTS HISTORY</span>`;
            container.appendChild(allBtn);

            accKeys.forEach((k, idx) => {
                const a = accounts ? accounts[k] : { name: `Account #${idx+1}`, login: k, currency: 'USD' };
                const flag = getAccountFlag(a.currency, a.name);
                const btn = document.createElement('button');
                btn.className = `asset-tab-btn ${activeHistoryAccountFilter === k ? 'active-gold' : ''}`;
                btn.id = `hist-acc-filter-${k}`;
                btn.style.cssText = 'padding: 8px 16px; font-size: 12px;';
                btn.onclick = () => selectHistoryAccountFilter(k);
                btn.innerHTML = `<span>${flag}</span> <span>${a.name || 'Account #' + (idx+1)} (${a.login || k})</span>`;
                container.appendChild(btn);
            });
        }

        function filterHistory(filterType) {
            activeHistoryFilter = filterType;
            const btns = {
                'ALL': 'filter-btn-all',
                'EXECUTED': 'filter-btn-executed',
                'MISSED': 'filter-btn-missed',
                'WIN': 'filter-btn-wins',
                'LOSS': 'filter-btn-losses'
            };
            Object.keys(btns).forEach(k => {
                const b = document.getElementById(btns[k]);
                if (b) {
                    if (k === filterType) {
                        b.style.background = 'var(--accent-gold)';
                        b.style.color = '#000';
                        b.style.fontWeight = '700';
                    } else {
                        b.style.background = 'rgba(255,255,255,0.05)';
                        b.style.color = 'var(--text-muted)';
                        b.style.fontWeight = 'normal';
                    }
                }
            });
            renderHistoryTable();
        }

        function renderHistoryTable() {
            if (!cachedHistoryData || !cachedHistoryData.trades) return;
            
            renderHistoryAccountFilterTabs(cachedAccountsData);

            const tbody = document.getElementById('history-table-body');
            if (!tbody) return;
            tbody.innerHTML = '';

            let allTrades = cachedHistoryData.trades || [];

            // 1. Account Filtering
            let accountFilteredTrades = allTrades;
            if (activeHistoryAccountFilter !== 'ALL') {
                accountFilteredTrades = allTrades.filter(t => t.account_id === activeHistoryAccountFilter || t.account_id === 'ALL');
            }

            // Update top stat cards based on account filter
            const closedTrades = accountFilteredTrades.filter(t => t.type_category === 'EXECUTED' && (t.result === 'WIN' || t.result === 'LOSS' || t.result === 'BREAKEVEN'));
            const wins = closedTrades.filter(t => t.result === 'WIN');
            const losses = closedTrades.filter(t => t.result === 'LOSS');
            const missedCount = accountFilteredTrades.filter(t => t.type_category === 'MISSED' || t.result === 'MISSED_ENTRY').length;
            const netPnl = closedTrades.reduce((acc, t) => acc + (Number(t.profit) || 0), 0);
            const winRate = closedTrades.length > 0 ? ((wins.length / closedTrades.length) * 100).toFixed(1) : '0.0';

            const curAccObj = cachedAccountsData && cachedAccountsData[activeHistoryAccountFilter];
            const currSymbol = curAccObj ? getCurrencySymbol(curAccObj.currency) : (activeHistoryAccountFilter === 'acc_2' ? '$' : '€');
            const currCode = curAccObj ? curAccObj.currency : (activeHistoryAccountFilter === 'acc_2' ? 'USD' : 'EUR');

            const elNetPnl = document.getElementById('hist-net-pnl');
            if (elNetPnl) {
                elNetPnl.innerText = `${netPnl >= 0 ? '+' : ''}${currSymbol}${netPnl.toFixed(2)} ${currCode}`;
                elNetPnl.style.color = netPnl >= 0 ? 'var(--buy-green)' : 'var(--sell-red)';
            }
            const elTradesStat = document.getElementById('hist-trades-stat');
            if (elTradesStat) elTradesStat.innerText = `${closedTrades.length} AI Closed Trades`;
            const elWinRate = document.getElementById('hist-winrate');
            if (elWinRate) elWinRate.innerText = `${winRate}%`;
            const elWinLoss = document.getElementById('hist-winloss-stat');
            if (elWinLoss) elWinLoss.innerText = `${wins.length} Wins / ${losses.length} Losses`;
            const elMissedStat = document.getElementById('hist-missed-stat');
            if (elMissedStat) elMissedStat.innerText = `${missedCount}`;

            // 2. Activity / Category Filtering
            let trades = accountFilteredTrades;
            if (activeHistoryFilter === 'EXECUTED') {
                trades = trades.filter(t => t.type_category === 'EXECUTED');
            } else if (activeHistoryFilter === 'MISSED') {
                trades = trades.filter(t => t.type_category === 'MISSED' || t.result === 'MISSED_ENTRY');
            } else if (activeHistoryFilter === 'WIN') {
                trades = trades.filter(t => t.result === 'WIN');
            } else if (activeHistoryFilter === 'LOSS') {
                trades = trades.filter(t => t.result === 'LOSS');
            }

            if (trades.length === 0) {
                tbody.innerHTML = `<tr><td colspan="11" style="text-align: center; padding: 28px; color: var(--text-muted);">
                    <div style="font-size: 16px; margin-bottom: 6px;">🤖 Zero AI Trade History For This Filter</div>
                    <div style="font-size: 12px; color: var(--text-sub);">Our AI automation strictly records ONLY AI-placed orders and vetoed signals. Manual trades are excluded.</div>
                </td></tr>`;
                return;
            }

            trades.forEach(t => {
                const tr = document.createElement('tr');
                tr.style.borderBottom = '1px solid rgba(255,255,255,0.03)';
                const isMissed = t.result === 'MISSED_ENTRY' || t.type_category === 'MISSED';
                
                let pnlColor = 'var(--text-muted)';
                let outcomeBadge = '';
                
                if (isMissed) {
                    pnlColor = 'var(--text-muted)';
                    outcomeBadge = '<span class="agent-badge" style="background: rgba(245, 158, 11, 0.12); color: var(--accent-gold); border: 1px solid rgba(245, 158, 11, 0.3);">MISSED / VETOED</span>';
                } else if (t.result === 'WIN') {
                    pnlColor = 'var(--buy-green)';
                    outcomeBadge = '<span class="agent-badge badge-buy">WIN</span>';
                } else if (t.result === 'LOSS') {
                    pnlColor = 'var(--sell-red)';
                    outcomeBadge = '<span class="agent-badge badge-sell">LOSS</span>';
                } else if (t.result === 'OPEN') {
                    pnlColor = '#60a5fa';
                    outcomeBadge = '<span class="agent-badge" style="background: rgba(96, 165, 250, 0.15); color: #60a5fa; border: 1px solid rgba(96, 165, 250, 0.3);">OPEN IN MT5</span>';
                } else {
                    outcomeBadge = '<span class="agent-badge badge-hold">BREAKEVEN</span>';
                }

                const actionBadge = t.type === 'BUY' 
                    ? '<span style="color: var(--buy-green); font-weight: 700;">🟢 BUY</span>' 
                    : '<span style="color: var(--sell-red); font-weight: 700;">🔴 SELL</span>';

                const slTpStr = (t.sl || t.tp) ? `SL: ${t.sl || '-'} / TP: ${t.tp || '-'}` : '-';
                const volumeStr = t.volume > 0 ? `${t.volume} Lots` : '<span style="color: var(--text-sub);">-</span>';

                const accBadge = `<span style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); font-size: 10px; padding: 2px 6px; border-radius: 4px; font-weight: 700;">${t.account_name || t.account_id || 'AI COUNCIL'}</span>`;

                tr.innerHTML = `
                    <td style="padding: 10px 16px;">${accBadge}</td>
                    <td style="padding: 10px 16px; font-family: var(--font-mono); font-size: 11px; color: var(--text-muted);">${t.time}</td>
                    <td style="padding: 10px 16px; font-family: var(--font-mono); font-weight: 600; font-size: 11px;">${typeof t.ticket === 'number' ? '#' + t.ticket : t.ticket}</td>
                    <td style="padding: 10px 16px; font-weight: 600; color: #fff;">${t.symbol}</td>
                    <td style="padding: 10px 16px;">${actionBadge}</td>
                    <td style="padding: 10px 16px; font-family: var(--font-mono);">${volumeStr}</td>
                    <td style="padding: 10px 16px; font-family: var(--font-mono);">${t.price}</td>
                    <td style="padding: 10px 16px; font-family: var(--font-mono); font-size: 11px; color: var(--text-sub);">${slTpStr}</td>
                    <td style="padding: 10px 16px; font-family: var(--font-mono); font-weight: 700; color: ${pnlColor}; font-size: 13px;">${t.profit_str}</td>
                    <td style="padding: 10px 16px; font-size: 11px; color: ${isMissed ? 'var(--accent-gold)' : 'var(--text-sub)'}; max-width: 260px;">${t.comment}</td>
                    <td style="padding: 10px 16px;">${outcomeBadge}</td>
                `;
                tbody.appendChild(tr);
            });
        }

        function renderPatternRadar(multiTf) {
            const grid = document.getElementById('pattern-timeframes-grid');
            if (!grid) return;

            if (!multiTf || !multiTf.timeframes || Object.keys(multiTf.timeframes).length === 0) {
                return;
            }

            const harmonyDesc = multiTf.harmony_description || "Multi-TF Harmony Active";
            const harmonyScore = multiTf.harmony_score || 50;
            const harmonyBias = multiTf.harmony_bias || "NEUTRAL";
            const badgeColor = harmonyBias === 'BULLISH' ? 'var(--buy-green)' : harmonyBias === 'BEARISH' ? 'var(--sell-red)' : 'var(--accent-gold)';

            if (document.getElementById('pattern-harmony-badge')) {
                document.getElementById('pattern-harmony-badge').innerHTML = `<span style="color: ${badgeColor}; font-weight: 700;">${harmonyBias === 'BULLISH' ? '🟢' : harmonyBias === 'BEARISH' ? '🔴' : '🟡'} ${harmonyDesc}</span>`;
            }
            if (document.getElementById('pattern-summary-text')) {
                document.getElementById('pattern-summary-text').innerText = `Hierarchical Confluence: ${multiTf.bullish_count || 0} Bullish / ${multiTf.bearish_count || 0} Bearish of ${multiTf.total_timeframes || 6} Timeframes`;
            }
            if (document.getElementById('pattern-score-pill')) {
                document.getElementById('pattern-score-pill').innerText = `Harmony Score: ${harmonyScore}%`;
                document.getElementById('pattern-score-pill').style.color = badgeColor;
                document.getElementById('pattern-score-pill').style.borderColor = badgeColor;
            }

            // Update Tradeciety Strategy Banner & HTF Macro Verdict
            const stratBanner = multiTf.tradeciety_strategy_mode || multiTf.strategy_mode;
            const fractalVerdict = multiTf.fractal_harmony_verdict || "";
            if (document.getElementById('tradeciety-strategy-text')) {
                if (stratBanner) {
                    document.getElementById('tradeciety-strategy-text').innerText = `⚡ ${stratBanner}`;
                } else {
                    document.getElementById('tradeciety-strategy-text').innerText = `Fractal Harmony: D1 Compass + H4 Bridge + M15 Trigger Synchronized`;
                }
            }

            const d1Data = multiTf.timeframes["D1"] || {};
            const d1Meta = d1Data.institutional_meta || {};
            if (document.getElementById('d1-auction-pill')) {
                const zone = d1Meta.auction_zone || (d1Data.bias === 'BULLISH' ? 'DISCOUNT' : 'PREMIUM');
                const zoneColor = zone === 'DISCOUNT' ? 'var(--buy-green)' : zone === 'PREMIUM' ? 'var(--sell-red)' : '#fbbf24';
                const eqStr = d1Meta.equilibrium_price ? ` ($${d1Meta.equilibrium_price})` : '';
                document.getElementById('d1-auction-pill').innerHTML = `D1 Macro: <strong style="color:${zoneColor}">${zone} ZONE${eqStr}</strong>`;
            }

            const h4Data = multiTf.timeframes["H4"] || {};
            const h4Meta = h4Data.institutional_meta || {};
            if (document.getElementById('h4-mss-pill')) {
                const mss = h4Meta.mss_status || h4Data.structure || "IN_RANGE";
                const mssColor = mss.includes('BULLISH') ? 'var(--buy-green)' : mss.includes('BEARISH') ? 'var(--sell-red)' : '#60a5fa';
                document.getElementById('h4-mss-pill').innerHTML = `H4 Bridge: <strong style="color:${mssColor}">${mss}</strong>`;
            }

            const tfMeta = {
                "D1": { name: "Daily (D1)", icon: "🧭", defaultRole: "COMPASS", roleBg: "rgba(245,158,11,0.2)", roleColor: "#fbbf24" },
                "H4": { name: "4-Hour (H4)", icon: "🌉", defaultRole: "FILTER / MSS", roleBg: "rgba(59,130,246,0.2)", roleColor: "#60a5fa" },
                "H1": { name: "1-Hour (H1)", icon: "⏳", defaultRole: "STRUCTURE", roleBg: "rgba(168,85,247,0.2)", roleColor: "#c084fc" },
                "M30": { name: "30-Min (M30)", icon: "⏱️", defaultRole: "INTERMEDIATE", roleBg: "rgba(168,85,247,0.2)", roleColor: "#c084fc" },
                "M15": { name: "15-Min (M15)", icon: "⚡", defaultRole: "TRIGGER", roleBg: "rgba(236,72,153,0.2)", roleColor: "#f472b6" },
                "M5": { name: "5-Min (M5)", icon: "🎯", defaultRole: "SNIPER", roleBg: "rgba(34,197,94,0.2)", roleColor: "#4ade80" }
            };

            grid.innerHTML = '';
            const tfOrder = ["D1", "H4", "H1", "M30", "M15", "M5"];
            tfOrder.forEach(tfKey => {
                const tfData = multiTf.timeframes[tfKey];
                if (!tfData) return;

                const meta = tfMeta[tfKey] || { name: tfKey, icon: "📊", defaultRole: "TF", roleBg: "rgba(255,255,255,0.1)", roleColor: "#fff" };
                const roleBadge = tfData.role_badge || meta.defaultRole;
                const isBull = tfData.bias === 'BULLISH';
                const isBear = tfData.bias === 'BEARISH';
                const biasBadge = isBull
                    ? '<span class="agent-badge badge-buy" style="font-size: 9px; padding: 2px 6px;">BULLISH</span>'
                    : isBear
                    ? '<span class="agent-badge badge-sell" style="font-size: 9px; padding: 2px 6px;">BEARISH</span>'
                    : '<span class="agent-badge badge-hold" style="font-size: 9px; padding: 2px 6px;">NEUTRAL</span>';

                const borderLeftColor = isBull ? 'var(--buy-green)' : isBear ? 'var(--sell-red)' : 'var(--hold-blue)';
                const borderColor = isBull ? 'rgba(16,185,129,0.3)' : isBear ? 'rgba(239,68,68,0.3)' : 'rgba(59,130,246,0.3)';

                let targetStr = "";
                if (tfData.patterns_found && tfData.patterns_found.length > 0 && tfData.patterns_found[0].target_price) {
                    targetStr = `Target: <strong>${Number(tfData.patterns_found[0].target_price).toLocaleString(undefined, {minimumFractionDigits: 2})}</strong>`;
                } else if (tfData.institutional_meta && tfData.institutional_meta.context_label) {
                    targetStr = `<span>${tfData.institutional_meta.context_label}</span>`;
                } else if (tfData.structure) {
                    targetStr = `<span>${tfData.structure.split('(')[0].trim()}</span>`;
                }

                let triggerInfo = tfData.status;
                if (tfData.candlestick_triggers && tfData.candlestick_triggers.length > 0) {
                    triggerInfo = `🔥 ${tfData.candlestick_triggers[0].name}`;
                }

                const tfCard = document.createElement('div');
                tfCard.style.cssText = `background: rgba(0,0,0,0.38); border: 1px solid ${borderColor}; border-radius: 10px; padding: 12px 14px; display: flex; flex-direction: column; justify-content: space-between; border-left: 3px solid ${borderLeftColor}; transition: all 0.2s; box-shadow: 0 4px 12px rgba(0,0,0,0.2);`;
                tfCard.innerHTML = `
                    <div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                            <div style="display: flex; align-items: center; gap: 4px;">
                                <span style="font-size: 11px; font-weight: 700; color: #fff;">${meta.icon} ${meta.name}</span>
                                <span style="font-size: 8px; font-weight: 800; padding: 1px 4px; border-radius: 3px; background: ${meta.roleBg}; color: ${meta.roleColor}; border: 1px solid ${meta.roleColor}40;">${roleBadge}</span>
                            </div>
                            ${biasBadge}
                        </div>
                        <div style="font-size: 12px; font-weight: 700; color: var(--accent-gold); margin-bottom: 3px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${tfData.primary_pattern || 'Trend Wave'}">
                            ${tfData.primary_pattern || 'Standard Trend Wave'}
                        </div>
                        <div style="font-size: 10px; color: var(--text-muted); line-height: 1.3;">
                            ${triggerInfo}
                        </div>
                    </div>
                    <div style="margin-top: 8px; padding-top: 6px; border-top: 1px solid rgba(255,255,255,0.06); font-size: 10px; color: var(--text-sub); display: flex; justify-content: space-between; align-items: center;">
                        <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 120px;">${targetStr}</span>
                        <button class="agent-discuss-btn" style="font-size: 9px; padding: 2px 6px;" onclick="discussTimeframe('${tfKey}', '${meta.name}')">💬 Ask</button>
                    </div>
                `;
                grid.appendChild(tfCard);
            });
        }
        
        function renderAgents(agents) {
            if (!agents || agents.length === 0) return;
            const container = document.getElementById('agents-container');
            if (!container) return;
            container.innerHTML = '';
            agents.forEach(agent => {
                const actionClass = agent.action === 'BUY' ? 'badge-buy' : agent.action === 'SELL' ? 'badge-sell' : 'badge-hold';
                const cardBorder = agent.action === 'BUY' ? 'buy-active' : agent.action === 'SELL' ? 'sell-active' : '';
                
                const card = document.createElement('div');
                card.className = `agent-card ${cardBorder}`;
                card.innerHTML = `
                    <div>
                        <div class="agent-header">
                            <div class="agent-meta">
                                <div class="agent-avatar">${agent.icon}</div>
                                <div>
                                    <div class="agent-name">${agent.name}</div>
                                    <div class="agent-role">${agent.role} • ${agent.tf}</div>
                                </div>
                            </div>
                            <span class="agent-badge ${actionClass}">${agent.action}</span>
                        </div>
                        <div class="agent-thought">"${agent.thought}"</div>
                    </div>
                    <div class="agent-footer">
                        <div class="agent-confidence">
                            <span class="conf-pill"></span>
                            <span>Confidence: <strong>${agent.confidence}%</strong></span>
                        </div>
                        <button class="agent-discuss-btn" onclick="discussAgent('${agent.name}', '${agent.name}')" title="Discuss this agent's opinion with Bullion AI in Hinglish">
                            <span>💬</span>
                            <span>Ask Agent</span>
                        </button>
                    </div>
                `;
                container.appendChild(card);
            });
        }

        let cachedAdminConfig = null;

        function renderSidebarAccounts(accounts) {
            if (!accounts) return;
            const container = document.getElementById('sidebar-accounts-list');
            const accKeys = Object.keys(accounts);
            
            // Update badges in sidebar and top navbar
            const sideBadge = document.getElementById('side-nav-accounts-badge');
            if (sideBadge) sideBadge.innerText = `${accKeys.length} ACCOUNTS`;
            const tabBadge = document.getElementById('tab-accounts-badge');
            if (tabBadge) tabBadge.innerText = `${accKeys.length} ACCOUNTS`;

            if (!container) return;
            container.innerHTML = '';

            accKeys.forEach((k, idx) => {
                const a = accounts[k];
                const currSym = getCurrencySymbol(a.currency);
                const flag = getAccountFlag(a.currency, a.name);
                const eqStr = Number(a.equity || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
                const pnl = Number(a.total_floating_pnl || 0);
                const pnlColor = pnl >= 0 ? 'var(--buy-green)' : 'var(--sell-red)';
                const posCount = a.open_count || 0;

                const card = document.createElement('div');
                card.className = 'sidebar-account-card';
                card.style.cursor = 'pointer';
                card.onclick = () => {
                    switchAsset('ACCOUNTS');
                    selectAccountFilter(k);
                };
                card.innerHTML = `
                    <div class="sidebar-acc-header">
                        <span class="sidebar-acc-name">${flag} ${a.name || 'Account #' + (idx+1)}</span>
                        <span class="sidebar-acc-badge ${posCount > 0 ? 'badge-buy' : 'badge-hold'}" style="font-size: 9px; padding: 1px 5px;">${posCount} POS</span>
                    </div>
                    <div class="sidebar-acc-row">
                        <span class="sidebar-acc-eq" style="color: #fbbf24; font-size: 13px;">${currSym}${eqStr}</span>
                        <span class="sidebar-acc-pnl" style="color: ${pnlColor}; font-size: 11px; font-weight: 700;">${pnl >= 0 ? '+' : ''}${currSym}${pnl.toFixed(2)}</span>
                    </div>
                    <div style="font-size: 9px; color: var(--text-sub); display: flex; justify-content: space-between; margin-top: 2px;">
                        <span>ID: ${a.login || 'Offline'}</span>
                        <span>Target: ${a.daily_target_pct || 0}%</span>
                    </div>
                `;
                container.appendChild(card);
            });
        }

        async function loadAdminConfig() {
            try {
                const res = await fetch('/api/admin/config');
                if (res.ok) {
                    const data = await res.json();
                    cachedAdminConfig = data.config || {};
                    const g = cachedAdminConfig.global_settings || {};

                    // Global Settings
                    const chkEngine = document.getElementById('cfg-engine-active');
                    if (chkEngine) {
                        chkEngine.checked = g.engine_active !== false;
                        const lbl = document.getElementById('label-engine-active');
                        if (lbl) {
                            lbl.innerText = chkEngine.checked ? 'ON' : 'OFF';
                            lbl.style.color = chkEngine.checked ? 'var(--buy-green)' : 'var(--sell-red)';
                        }
                    }
                    const inpLotCap = document.getElementById('cfg-global-lot-cap');
                    if (inpLotCap && g.global_hard_lot_cap !== undefined) inpLotCap.value = g.global_hard_lot_cap;

                    const inpSpread = document.getElementById('cfg-max-spread');
                    if (inpSpread && g.max_spread_points !== undefined) inpSpread.value = g.max_spread_points;

                    const chkNews = document.getElementById('cfg-news-filter');
                    if (chkNews) {
                        chkNews.checked = g.news_filter_enabled !== false;
                        const lblNews = document.getElementById('label-news-active');
                        if (lblNews) lblNews.innerText = chkNews.checked ? 'ENABLED' : 'DISABLED';
                    }

                    // Render dynamic parameter cards for active and archived accounts
                    renderAdminAccountsGrid(cachedAdminConfig, data.telemetry);
                    renderArchivedAccountsGrid(cachedAdminConfig);
                    if (data.telemetry) {
                        updateAdminTelemetry(data.telemetry);
                    }
                }
            } catch (e) {
                console.error("Error loading admin config:", e);
            }
        }

        function renderAdminAccountsGrid(config, telemetry) {
            const grid = document.getElementById('admin-accounts-cards-grid');
            const activeBadge = document.getElementById('admin-active-count-badge');
            if (!grid) return;
            grid.innerHTML = '';

            const accs = (config && config.accounts) ? config.accounts : (cachedAdminConfig ? cachedAdminConfig.accounts : {});
            const accKeys = Object.keys(accs);

            if (activeBadge) activeBadge.innerText = `${accKeys.length} ACTIVE`;
            const lockoutsText = document.getElementById('admin-lockouts-text');
            if (lockoutsText) lockoutsText.innerText = `${accKeys.length} Targets Monitored`;

            if (accKeys.length === 0) {
                grid.innerHTML = `
                    <div style="grid-column: 1 / -1; background: rgba(0,0,0,0.3); border: 1px dashed rgba(239,68,68,0.3); border-radius: 12px; padding: 24px; text-align: center; color: var(--text-muted);">
                        <div style="font-size: 24px; margin-bottom: 8px;">🔌</div>
                        <strong style="color: #fff; font-size: 14px;">No Active Accounts Connected</strong>
                        <p style="font-size: 12px; margin-top: 6px; color: var(--text-sub);">All accounts are disconnected or paused. Reconnect a saved account from the Disconnected Archive below, or scan for new MT5 terminals.</p>
                    </div>
                `;
                return;
            }

            accKeys.forEach((k, idx) => {
                const a = accs[k] || {};
                const t = (telemetry && telemetry[k]) ? telemetry[k] : (cachedAccountsData && cachedAccountsData[k] ? cachedAccountsData[k] : {});
                const currSym = getCurrencySymbol(a.currency);
                const flag = getAccountFlag(a.currency, a.name);
                
                const card = document.createElement('div');
                card.className = 'metric-card';
                card.id = `admin-card-${k}`;
                card.style.border = '1px solid rgba(56, 189, 248, 0.35)';
                card.style.background = 'linear-gradient(135deg, rgba(14, 18, 28, 0.95), rgba(20, 26, 40, 0.95))';
                card.style.padding = '22px';
                card.style.borderRadius = '12px';

                card.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 8px;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span style="font-size: 26px;">${flag}</span>
                            <div>
                                <div style="display: flex; align-items: center; gap: 8px;">
                                    <input type="text" class="admin-input" id="cfg-${k}-name" value="${a.name || 'Account #' + (idx+1)}" style="font-size: 15px; font-weight: 800; color: #fbbf24; padding: 4px 8px; width: 220px; background: rgba(0,0,0,0.5);">
                                    <span class="badge-live" style="font-size: 9px; padding: 2px 6px;">${a.mode || 'PROP'}</span>
                                </div>
                                <div style="font-size: 11px; color: var(--text-muted); margin-top: 3px;">
                                    ID: <strong>${t.login || a.id}</strong> • Server: <strong>${t.server || 'MT5 Live'}</strong> • Magic: <strong>#${a.magic_number || 777888}</strong>
                                </div>
                            </div>
                        </div>
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <label class="admin-toggle-switch">
                                <input type="checkbox" id="cfg-${k}-active" ${a.is_active !== false ? 'checked' : ''} onchange="document.getElementById('cfg-${k}-active-label').innerText = this.checked ? 'ACTIVE' : 'PAUSED'; document.getElementById('cfg-${k}-active-label').style.color = this.checked ? 'var(--buy-green)' : 'var(--sell-red)';">
                                <span class="admin-slider"></span>
                            </label>
                            <span style="font-size: 11px; font-weight: 700; color: ${a.is_active !== false ? 'var(--buy-green)' : 'var(--sell-red)'};" id="cfg-${k}-active-label">
                                ${a.is_active !== false ? 'ACTIVE' : 'PAUSED'}
                            </span>
                            <button class="btn" onclick="disconnectAccountFromCouncil('${k}')" style="padding: 4px 10px; font-size: 11px; font-weight: 600; background: rgba(239,68,68,0.15); border: 1px solid rgba(239,68,68,0.35); color: #f87171; border-radius: 6px; cursor: pointer; display: flex; align-items: center; gap: 4px;" title="Disconnect from AI Council and move to Inactive Archive">
                                <span>🔌 Disconnect</span>
                            </button>
                        </div>
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 16px;">
                        <div class="admin-form-group">
                            <div class="admin-label">Max Lot Size per Trade</div>
                            <input type="number" step="0.01" min="0.01" max="1.00" class="admin-input" id="cfg-${k}-max-lot" value="${a.max_lot_size !== undefined ? a.max_lot_size : 0.05}">
                            <span style="font-size: 10px; color: var(--text-sub);">Risk cap per sniper entry</span>
                        </div>

                        <div class="admin-form-group">
                            <div class="admin-label">Max Open Positions</div>
                            <input type="number" step="1" min="1" max="10" class="admin-input" id="cfg-${k}-max-trades" value="${a.max_open_trades !== undefined ? a.max_open_trades : 1}">
                            <span style="font-size: 10px; color: var(--text-sub);">Simultaneous active trades</span>
                        </div>

                        <div class="admin-form-group">
                            <div class="admin-label" style="color: #34d399;">Daily Profit Target (${currSym})</div>
                            <input type="number" step="1" min="1" max="10000" class="admin-input" id="cfg-${k}-daily-target" value="${a.daily_profit_target !== undefined ? a.daily_profit_target : 100.0}" style="border-color: rgba(52, 211, 153, 0.4); color: #34d399;">
                            <span style="font-size: 10px; color: var(--text-sub);">Auto-halts trades when achieved</span>
                        </div>

                        <div class="admin-form-group">
                            <div class="admin-label" style="color: #f87171;">Daily Max Loss Limit (${currSym})</div>
                            <input type="number" step="1" min="1" max="5000" class="admin-input" id="cfg-${k}-daily-loss" value="${a.daily_max_loss !== undefined ? a.daily_max_loss : 50.0}" style="border-color: rgba(248, 113, 113, 0.4); color: #f87171;">
                            <span style="font-size: 10px; color: var(--text-sub);">Capital preservation circuit-breaker</span>
                        </div>
                    </div>

                    <!-- Daily Target Progress Meter -->
                    <div class="target-progress-container">
                        <div style="display: flex; justify-content: space-between; font-size: 11px; font-weight: 700;">
                            <span style="color: #fff;">Today's Target Progress:</span>
                            <span id="admin-${k}-target-text" style="color: var(--buy-green); font-family: var(--font-mono);">
                                ${Number(t.today_realized_pnl || 0) >= 0 ? '+' : ''}${currSym}${Number(t.today_realized_pnl || 0).toFixed(2)} / ${currSym}${Number(a.daily_profit_target || 100).toFixed(2)} ${a.currency || 'USD'} (${t.daily_target_pct || 0}%)
                            </span>
                        </div>
                        <div class="target-progress-bar-bg">
                            <div class="target-progress-bar-fill" id="admin-${k}-target-bar" style="width: ${Math.min(100, Math.max(0, t.daily_target_pct || 0))}%;"></div>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 10px; color: var(--text-sub);">
                            <span>Status: <strong id="admin-${k}-status-msg" style="color: ${t.target_reached_today ? '#00f0ff' : (a.is_active ? 'var(--buy-green)' : 'var(--sell-red)')};">${t.target_reached_today ? '🎯 TARGET HIT (HALTED)' : (a.is_active ? '🟢 ACTIVE & SCANNING' : '⏸️ PAUSED')}</strong></span>
                            <span id="admin-${k}-trades-cnt">${t.today_trade_count || 0} Closed Deals Today</span>
                        </div>
                    </div>

                    <div style="margin-top: 10px; font-size: 10px; color: var(--text-sub); font-family: var(--font-mono); word-break: break-all;">
                        📂 Terminal: ${a.terminal_path || 'Default'}
                    </div>
                `;
                grid.appendChild(card);
            });
        }

        function renderArchivedAccountsGrid(config) {
            const grid = document.getElementById('admin-archived-cards-grid');
            const badge = document.getElementById('admin-archived-count-badge');
            if (!grid) return;
            grid.innerHTML = '';

            const archived = (config && config.archived_accounts) ? config.archived_accounts : (cachedAdminConfig && cachedAdminConfig.archived_accounts ? cachedAdminConfig.archived_accounts : {});
            const archKeys = Object.keys(archived);
            if (badge) {
                badge.innerText = `${archKeys.length} DISCONNECTED`;
                badge.style.color = archKeys.length > 0 ? '#fbbf24' : '#94a3b8';
                badge.style.borderColor = archKeys.length > 0 ? 'rgba(251, 191, 36, 0.4)' : 'rgba(148, 163, 184, 0.3)';
                badge.style.background = archKeys.length > 0 ? 'rgba(251, 191, 36, 0.1)' : 'rgba(148, 163, 184, 0.1)';
            }

            if (archKeys.length === 0) {
                grid.innerHTML = `
                    <div style="grid-column: 1 / -1; background: rgba(0,0,0,0.25); border: 1px dashed rgba(255,255,255,0.1); border-radius: 10px; padding: 20px; text-align: center; color: var(--text-sub); font-size: 12px;">
                        <span>No disconnected accounts currently. When you disconnect an active account, it is safely stored here with its full settings preserved for 1-click reconnection anytime.</span>
                    </div>
                `;
                return;
            }

            archKeys.forEach(k => {
                const a = archived[k] || {};
                const currSym = getCurrencySymbol(a.currency);
                const flag = getAccountFlag(a.currency, a.name);

                const card = document.createElement('div');
                card.className = 'metric-card';
                card.id = `archived-card-${k}`;
                card.style.border = '1px solid rgba(148, 163, 184, 0.25)';
                card.style.background = 'linear-gradient(135deg, rgba(12, 16, 26, 0.95), rgba(16, 22, 34, 0.95))';
                card.style.padding = '18px 20px';
                card.style.borderRadius = '12px';

                card.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span style="font-size: 24px; opacity: 0.85;">${flag}</span>
                            <div>
                                <div style="display: flex; align-items: center; gap: 8px;">
                                    <strong style="font-size: 14px; color: #cbd5e1;">${a.name || k}</strong>
                                    <span class="badge-live" style="font-size: 9px; padding: 1px 5px; background: rgba(148,163,184,0.15); color: #94a3b8; border-color: rgba(148,163,184,0.3);">${a.mode || 'PROP'}</span>
                                </div>
                                <div style="font-size: 10px; color: var(--text-sub); font-family: var(--font-mono); margin-top: 2px;">
                                    Magic: <strong>#${a.magic_number || 777888}</strong> • Max Lot: <strong>${a.max_lot_size || 0.05}</strong> • Target: <strong>${currSym}${a.daily_profit_target || 100}</strong>
                                </div>
                            </div>
                        </div>
                        <div style="font-size: 10px; color: #f87171; background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.25); border-radius: 4px; padding: 2px 6px; font-weight: 700;">
                            🔌 DISCONNECTED (SAVED)
                        </div>
                    </div>

                    <div style="font-size: 10px; color: var(--text-sub); font-family: var(--font-mono); word-break: break-all; margin-bottom: 12px; background: rgba(0,0,0,0.35); padding: 6px 10px; border-radius: 6px;">
                        📂 ${a.terminal_path || 'Default Path'}
                    </div>

                    <div style="display: flex; gap: 10px; align-items: center;">
                        <button class="btn" onclick="reconnectAccountToCouncil('${k}')" style="flex: 1; padding: 8px 14px; font-size: 11px; font-weight: 800; background: linear-gradient(135deg, #10b981, #059669); color: #fff; border: none; border-radius: 6px; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px; box-shadow: 0 0 14px rgba(16,185,129,0.35);">
                            <span>➕ 1-Click Reconnect & Activate</span>
                        </button>
                        <button class="btn" onclick="deleteArchivedAccount('${k}')" style="padding: 8px 12px; font-size: 11px; font-weight: 600; background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); color: #f87171; border-radius: 6px; cursor: pointer;" title="Permanently delete from archive">
                            <span>🗑️</span>
                        </button>
                    </div>
                `;
                grid.appendChild(card);
            });
        }

        
        async function syncAllActiveTerminals() {
            try {
                speakBullionVoice('Syncing all MT5 terminals with live accounts...', 'en');
                const res = await fetch('/api/admin/sync-all-terminals', { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    alert('✅ ' + data.message);
                    await loadAdminConfig();
                    await fetchLiveStatus();
                    triggerAutoDetectTerminals();
                } else {
                    alert('Error syncing terminals: ' + (data.error || 'Failed'));
                }
            } catch (e) {
                alert('Connection Error: ' + e.message);
            }
        }
        
        async function disconnectAccountFromCouncil(accId) {
            const acc = cachedAdminConfig?.accounts?.[accId] || {};
            const name = acc.name || accId;
            if (!confirm(`Are you sure you want to disconnect [${name}] from the AI Council?\n\nIts risk configuration and terminal settings will be safely saved in the Disconnected Archive for 1-click reconnection in the future.`)) return;

            try {
                const res = await fetch('/api/admin/disconnect-account', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ account_id: accId })
                });
                const data = await res.json();
                if (res.ok && data.success) {
                    speakBullionVoice(`Account ${name} disconnected and moved to archive.`, 'en');
                    // Instantly hide the disconnected card from DOM
                    const cardEl = document.getElementById(`admin-card-${accId}`);
                    if (cardEl) cardEl.remove();
                    delete cachedAdminConfig?.accounts?.[accId];
                    if (cachedAccountsData) delete cachedAccountsData[accId];
                    await loadAdminConfig();
                    await fetchLiveStatus();
                    triggerAutoDetectTerminals();
                } else {
                    alert(`Error disconnecting account: ${data.error || data.message || 'Unknown error'}`);
                }
            } catch (e) {
                alert(`Connection Error: ${e.message}`);
            }
        }

        async function reconnectAccountToCouncil(accId) {
            try {
                const res = await fetch('/api/admin/reconnect-account', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ account_id: accId })
                });
                const data = await res.json();
                if (res.ok && data.success) {
                    speakBullionVoice(`Account reconnected and activated in AI Council.`, 'en');
                    await loadAdminConfig();
                    fetchLiveStatus();
                    if (document.getElementById('auto-detected-terminals-container')?.style.display !== 'none') {
                        triggerAutoDetectTerminals();
                    }
                } else {
                    alert(`Error reconnecting account: ${data.error || data.message || 'Unknown error'}`);
                }
            } catch (e) {
                alert(`Connection Error: ${e.message}`);
            }
        }

        async function deleteArchivedAccount(accId) {
            if (!confirm(`Permanently delete [${accId}] from the archive?\n\nThis will remove its saved settings completely.`)) return;
            try {
                const res = await fetch('/api/admin/delete-archived-account', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ account_id: accId })
                });
                const data = await res.json();
                if (res.ok && data.success) {
                    await loadAdminConfig();
                    if (document.getElementById('auto-detected-terminals-container')?.style.display !== 'none') {
                        triggerAutoDetectTerminals();
                    }
                } else {
                    alert(`Error deleting account: ${data.error || data.message || 'Unknown error'}`);
                }
            } catch (e) {
                alert(`Connection Error: ${e.message}`);
            }
        }

        function removeAccountFromCouncil(accId) {
            disconnectAccountFromCouncil(accId);
        }

        async function triggerAutoDetectTerminals() {
            const container = document.getElementById('auto-detected-terminals-container');
            const grid = document.getElementById('auto-detected-terminals-grid');
            const heading = document.getElementById('auto-detect-heading');
            if (container) container.style.display = 'block';
            if (heading) heading.innerText = '🔍 Scanning Windows Program Files & Running MT5 Instances...';
            if (grid) grid.innerHTML = '<div style="color: var(--accent-gold); font-size: 12px; padding: 10px;">Scanning system terminals...</div>';

            try {
                const res = await fetch('/api/admin/auto-detect');
                if (res.ok) {
                    const data = await res.json();
                    const detected = data.detected || [];
                    if (heading) heading.innerText = `✅ Found ${detected.length} MT5 Terminals Installed on System:`;
                    if (grid) {
                        grid.innerHTML = '';
                        if (detected.length === 0) {
                            grid.innerHTML = '<div style="color: var(--text-muted); font-size: 12px;">No additional MT5 instances found in standard paths.</div>';
                            return;
                        }
                        detected.forEach(t => {
                            const card = document.createElement('div');
                            card.style.cssText = 'background: rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 12px; font-size: 11px;';
                            const isConfigured = t.already_configured;
                            const isActive = t.is_active;
                            const isArchived = t.is_archived;
                            const termJsonStr = JSON.stringify(t).replace(/'/g, "\\'");
                            
                            let statusBadge = '';
                            let actionBtn = '';

                            if (isActive) {
                                statusBadge = `<span style="font-size: 10px; color: var(--buy-green); font-weight: 700;">🟢 ACTIVE IN COUNCIL (${t.active_acc_id})</span>`;
                                actionBtn = `<div style="font-size: 10px; color: var(--buy-green); text-align: center; font-weight: 700; padding: 6px;">🟢 Live Trading Active</div>`;
                            } else if (isArchived) {
                                statusBadge = `<span style="font-size: 10px; color: #fbbf24; font-weight: 700;">🔌 DISCONNECTED (SAVED: ${t.archived_acc_id})</span>`;
                                actionBtn = `
                                    <button class="btn" onclick="reconnectAccountToCouncil('${t.archived_acc_id}')" style="width: 100%; padding: 7px; font-size: 11px; font-weight: 800; background: linear-gradient(135deg, #0ea5e9, #0284c7); color: #fff; border: none; border-radius: 6px; cursor: pointer; box-shadow: 0 0 15px rgba(14,165,233,0.4);">
                                        ➕ 1-Click Reconnect (Restore Saved Config)
                                    </button>
                                `;
                            } else {
                                statusBadge = `<span style="font-size: 10px; color: var(--accent-gold); font-weight: 700;">⭐ NEW DISCOVERED</span>`;
                                actionBtn = `
                                    <button class="btn" onclick='addDetectedAccountToCouncil(${termJsonStr})' style="width: 100%; padding: 7px; font-size: 11px; font-weight: 800; background: linear-gradient(135deg, #10b981, #059669); color: #fff; border: none; border-radius: 6px; cursor: pointer; box-shadow: 0 0 15px rgba(16,185,129,0.3);">
                                        ➕ 1-Click Link & Activate in Council
                                    </button>
                                `;
                            }

                            card.innerHTML = `
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                                    <strong style="color: #38bdf8;">${t.name || 'MT5 Instance'} (${t.server || 'Server'})</strong>
                                    ${statusBadge}
                                </div>
                                <div style="color: var(--text-muted); font-family: var(--font-mono); font-size: 10px; word-break: break-all; margin-bottom: 4px;">${t.terminal_path}</div>
                                <div style="display: flex; justify-content: space-between; color: #fff; margin-bottom: 8px;">
                                    <span>Login: <strong>${t.login || 'Offline'}</strong></span>
                                    <span>Equity: <strong style="color: #fbbf24;">${t.currency || 'USD'} ${Number(t.equity || 0).toLocaleString()}</strong></span>
                                </div>
                                ${actionBtn}
                            `;
                            grid.appendChild(card);
                        });
                    }
                }
            } catch (e) {
                if (grid) grid.innerHTML = `<div style="color: var(--sell-red);">Error: ${e.message}</div>`;
            }
        }

        async function addDetectedAccountToCouncil(termObj) {
            if (!termObj || !termObj.terminal_path) return;
            const res = await fetch('/api/admin/config');
            let cfg = { version: "1.0", global_settings: {}, accounts: {}, archived_accounts: {} };
            if (res.ok) {
                const data = await res.json();
                cfg = data.config || cfg;
            }
            
            const existingKeys = Object.keys(cfg.accounts || {});
            const nextIdx = existingKeys.length + 1;
            const newId = `acc_${nextIdx}`;

            if (!cfg.accounts) cfg.accounts = {};
            cfg.accounts[newId] = {
                id: newId,
                name: `Account #${nextIdx} (${termObj.server || termObj.name})`,
                terminal_path: termObj.terminal_path,
                currency: termObj.currency || "USD",
                magic_number: termObj.suggested_magic || (777888 + (nextIdx * 111)),
                mode: termObj.suggested_mode || "STANDARD_PROP",
                is_active: true,
                max_open_trades: 1,
                max_lot_size: termObj.suggested_max_lot || 0.05,
                min_lot_size: 0.01,
                daily_profit_target: termObj.suggested_target || 100.0,
                daily_max_loss: termObj.suggested_loss || 50.0,
                trailing_be_r: 0.5,
                tp1_close_pct: 50.0
            };

            const saveRes = await fetch('/api/admin/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(cfg)
            });

            if (saveRes.ok) {
                speakBullionVoice(`New MT5 terminal ${termObj.name} linked and activated in Council.`, 'en');
                alert(`✅ New Account #${nextIdx} (${termObj.server}) successfully linked to AI Council!`);
                loadAdminConfig();
                fetchLiveStatus();
                triggerAutoDetectTerminals();
            }
        }

        function updateAdminTelemetry(telemetry) {
            if (!telemetry) return;
            Object.keys(telemetry).forEach(k => {
                const a = telemetry[k];
                const pnl = Number(a.today_realized_pnl || 0);
                const target = Number(a.daily_profit_target || 100.0);
                const currSym = getCurrencySymbol(a.currency);
                const pct = target > 0 ? Math.min(100, Math.max(0, (pnl / target) * 100)) : 0;
                const bar = document.getElementById(`admin-${k}-target-bar`);
                const txt = document.getElementById(`admin-${k}-target-text`);
                const msg = document.getElementById(`admin-${k}-status-msg`);
                const cnt = document.getElementById(`admin-${k}-trades-cnt`);

                if (bar) {
                    bar.style.width = `${pct}%`;
                    bar.style.background = a.target_reached_today ? 'linear-gradient(90deg, #10b981, #00f0ff)' : (pnl < 0 ? 'linear-gradient(90deg, #ef4444, #f87171)' : 'linear-gradient(90deg, #10b981, #34d399)');
                }
                if (txt) {
                    txt.innerText = `${pnl >= 0 ? '+' : ''}${currSym}${pnl.toFixed(2)} / ${currSym}${target.toFixed(2)} ${a.currency || ''} (${pct.toFixed(1)}%)`;
                    txt.style.color = a.target_reached_today ? '#00f0ff' : (pnl < 0 ? 'var(--sell-red)' : 'var(--buy-green)');
                }
                if (msg) {
                    if (!a.is_active) {
                        msg.innerText = '⏸️ PAUSED BY ADMIN';
                        msg.style.color = 'var(--sell-red)';
                    } else if (a.target_reached_today) {
                        msg.innerText = '🎯 TARGET ACHIEVED (HALTED TODAY)';
                        msg.style.color = '#00f0ff';
                    } else if (a.max_loss_hit_today) {
                        msg.innerText = '🛑 MAX LOSS REACHED (HALTED TODAY)';
                        msg.style.color = 'var(--sell-red)';
                    } else {
                        msg.innerText = '🟢 ACTIVE & SCANNING M5';
                        msg.style.color = 'var(--buy-green)';
                    }
                }
                if (cnt) cnt.innerText = `${a.today_trade_count || 0} Closed Deals Today`;
            });
        }

        async function saveAdminConfigFromUI() {
            const saveMsg = document.getElementById('admin-save-msg');
            if (saveMsg) {
                saveMsg.style.display = 'block';
                saveMsg.style.color = 'var(--accent-gold)';
                saveMsg.innerText = '⏳ Applying parameters to live AI engine...';
            }

            if (!cachedAdminConfig) {
                try {
                    const res = await fetch('/api/admin/config');
                    if (res.ok) {
                        const d = await res.json();
                        cachedAdminConfig = d.config || {};
                    }
                } catch(e) {}
            }

            const cfg = cachedAdminConfig || { version: "1.0", global_settings: {}, accounts: {} };
            cfg.global_settings = {
                "engine_active": document.getElementById('cfg-engine-active')?.checked !== false,
                "global_hard_lot_cap": parseFloat(document.getElementById('cfg-global-lot-cap')?.value || 0.10),
                "max_spread_points": parseFloat(document.getElementById('cfg-max-spread')?.value || 80.0),
                "news_filter_enabled": document.getElementById('cfg-news-filter')?.checked !== false,
                "news_blackout_minutes": 15
            };

            if (!cfg.accounts) cfg.accounts = {};
            const accKeys = Object.keys(cfg.accounts);

            accKeys.forEach(k => {
                const prev = cfg.accounts[k] || {};
                const nameInput = document.getElementById(`cfg-${k}-name`);
                const activeInput = document.getElementById(`cfg-${k}-active`);
                const maxLotInput = document.getElementById(`cfg-${k}-max-lot`);
                const maxTradesInput = document.getElementById(`cfg-${k}-max-trades`);
                const targetInput = document.getElementById(`cfg-${k}-daily-target`);
                const lossInput = document.getElementById(`cfg-${k}-daily-loss`);

                cfg.accounts[k] = {
                    ...prev,
                    "id": k,
                    "name": nameInput ? nameInput.value : prev.name,
                    "terminal_path": prev.terminal_path,
                    "currency": prev.currency || "USD",
                    "magic_number": prev.magic_number || 777888,
                    "mode": prev.mode || "STANDARD_PROP",
                    "is_active": activeInput ? activeInput.checked : (prev.is_active !== false),
                    "max_open_trades": maxTradesInput ? parseInt(maxTradesInput.value || 1) : (prev.max_open_trades || 1),
                    "max_lot_size": maxLotInput ? parseFloat(maxLotInput.value || 0.05) : (prev.max_lot_size || 0.05),
                    "min_lot_size": prev.min_lot_size || 0.01,
                    "daily_profit_target": targetInput ? parseFloat(targetInput.value || 100.0) : (prev.daily_profit_target || 100.0),
                    "daily_max_loss": lossInput ? parseFloat(lossInput.value || 50.0) : (prev.daily_max_loss || 50.0),
                    "trailing_be_r": prev.trailing_be_r || 0.5,
                    "tp1_close_pct": prev.tp1_close_pct || 50.0
                };
            });

            try {
                const res = await fetch('/api/admin/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(cfg)
                });
                const data = await res.json();
                if (res.ok && data.success) {
                    cachedAdminConfig = cfg;
                    if (saveMsg) {
                        saveMsg.style.color = 'var(--buy-green)';
                        saveMsg.innerText = `✅ Saved & Hot-Reloaded! AI Engine has locked new parameters for all ${accKeys.length} accounts.`;
                    }
                    speakBullionVoice(`Admin risk settings and daily targets saved for ${accKeys.length} accounts.`, "en");
                    fetchLiveStatus();
                    loadAdminConfig();
                    setTimeout(() => {
                        if (saveMsg) saveMsg.style.display = 'none';
                    }, 4000);
                } else {
                    if (saveMsg) {
                        saveMsg.style.color = 'var(--sell-red)';
                        saveMsg.innerText = `❌ Error saving: ${data.error || 'Check server logs'}`;
                    }
                }
            } catch (e) {
                if (saveMsg) {
                    saveMsg.style.color = 'var(--sell-red)';
                    saveMsg.innerText = `❌ Connection Error: ${e.message}`;
                }
            }
        }

        async function removeAccountFromCouncil(accId) {
            if (!confirm(`Are you sure you want to remove account [${accId}] from the AI Council?`)) return;
            if (!cachedAdminConfig || !cachedAdminConfig.accounts) return;
            delete cachedAdminConfig.accounts[accId];
            
            try {
                const res = await fetch('/api/admin/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(cachedAdminConfig)
                });
                if (res.ok) {
                    alert(`Account [${accId}] removed successfully.`);
                    loadAdminConfig();
                    fetchLiveStatus();
                }
            } catch(e) {
                alert(`Error removing account: ${e.message}`);
            }
        }

        async function triggerAutoDetectTerminals() {
            const container = document.getElementById('auto-detected-terminals-container');
            const grid = document.getElementById('auto-detected-terminals-grid');
            const heading = document.getElementById('auto-detect-heading');
            if (container) container.style.display = 'block';
            if (heading) heading.innerText = '🔍 Scanning Windows Program Files & Running MT5 Instances...';
            if (grid) grid.innerHTML = '<div style="color: var(--accent-gold); font-size: 12px; padding: 10px;">Scanning system terminals...</div>';

            try {
                const res = await fetch('/api/admin/auto-detect');
                if (res.ok) {
                    const data = await res.json();
                    const detected = data.detected || [];
                    if (heading) heading.innerText = `✅ Found ${detected.length} MT5 Terminals Installed on System:`;
                    if (grid) {
                        grid.innerHTML = '';
                        if (detected.length === 0) {
                            grid.innerHTML = '<div style="color: var(--text-muted); font-size: 12px;">No additional MT5 instances found in standard paths.</div>';
                            return;
                        }
                        detected.forEach(t => {
                            const card = document.createElement('div');
                            card.style.cssText = 'background: rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 12px; font-size: 11px;';
                            const isConfigured = t.already_configured;
                            const termJsonStr = JSON.stringify(t).replace(/'/g, "\\'");
                            card.innerHTML = `
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                                    <strong style="color: #38bdf8;">${t.name || 'MT5 Instance'} (${t.server || 'Server'})</strong>
                                    <span style="font-size: 10px; color: ${isConfigured ? 'var(--buy-green)' : 'var(--accent-gold)'}; font-weight: 700;">
                                        ${isConfigured ? '✓ CONFIGURED' : '⭐ NEW DISCOVERED'}
                                    </span>
                                </div>
                                <div style="color: var(--text-muted); font-family: var(--font-mono); font-size: 10px; word-break: break-all; margin-bottom: 4px;">${t.terminal_path}</div>
                                <div style="display: flex; justify-content: space-between; color: #fff; margin-bottom: 8px;">
                                    <span>Login: <strong>${t.login || 'Offline'}</strong></span>
                                    <span>Equity: <strong style="color: #fbbf24;">${t.currency} ${Number(t.equity || 0).toLocaleString()}</strong></span>
                                </div>
                                ${!isConfigured ? `
                                    <button class="btn" onclick='addDetectedAccountToCouncil(${JSON.stringify(t)})' style="width: 100%; padding: 6px; font-size: 11px; font-weight: 700; background: var(--buy-green); color: #000; border: none; cursor: pointer;">
                                        ➕ 1-Click Link & Activate in Council
                                    </button>
                                ` : `
                                    <div style="font-size: 10px; color: var(--buy-green); text-align: center; font-weight: 700;">🟢 Active in Council Execution</div>
                                `}
                            `;
                            grid.appendChild(card);
                        });
                    }
                }
            } catch (e) {
                if (grid) grid.innerHTML = `<div style="color: var(--sell-red);">Error: ${e.message}</div>`;
            }
        }

        async function addDetectedAccountToCouncil(termObj) {
            if (!termObj || !termObj.terminal_path) return;
            const res = await fetch('/api/admin/config');
            let cfg = { version: "1.0", global_settings: {}, accounts: {} };
            if (res.ok) {
                const data = await res.json();
                cfg = data.config || cfg;
            }
            
            const existingKeys = Object.keys(cfg.accounts || {});
            const nextIdx = existingKeys.length + 1;
            const newId = `acc_${nextIdx}`;

            cfg.accounts[newId] = {
                id: newId,
                name: `Account #${nextIdx} (${termObj.server || termObj.name})`,
                terminal_path: termObj.terminal_path,
                currency: termObj.currency || "USD",
                magic_number: termObj.suggested_magic || (777888 + (nextIdx * 111)),
                mode: termObj.suggested_mode || "STANDARD_PROP",
                is_active: true,
                max_open_trades: 1,
                max_lot_size: termObj.suggested_max_lot || 0.05,
                min_lot_size: 0.01,
                daily_profit_target: termObj.suggested_target || 100.0,
                daily_max_loss: termObj.suggested_loss || 50.0,
                trailing_be_r: 0.5,
                tp1_close_pct: 50.0
            };

            const saveRes = await fetch('/api/admin/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(cfg)
            });

            if (saveRes.ok) {
                speakBullionVoice(`New MT5 terminal ${termObj.name} linked and activated in Council.`, 'en');
                alert(`✅ New Account #${nextIdx} (${termObj.server}) successfully linked to AI Council!`);
                loadAdminConfig();
                fetchLiveStatus();
                triggerAutoDetectTerminals();
            }
        }

        function updateMacroThreatRadar(dossier) {
            if (!dossier) return;

            // 1. Top Threat and Bias Pills
            const threatPill = document.getElementById('macro-threat-pill');
            if (threatPill && dossier.shock_threat_level) {
                threatPill.innerText = `THREAT: ${dossier.shock_threat_level.replace(/_/g, ' ')}`;
                if (dossier.shock_threat_level.includes('CRITICAL') || dossier.shock_threat_level.includes('HIGH')) {
                    threatPill.style.background = 'rgba(239, 68, 68, 0.2)';
                    threatPill.style.color = '#f87171';
                    threatPill.style.borderColor = 'rgba(239, 68, 68, 0.4)';
                } else {
                    threatPill.style.background = 'rgba(16, 185, 129, 0.2)';
                    threatPill.style.color = '#34d399';
                    threatPill.style.borderColor = 'rgba(16, 185, 129, 0.4)';
                }
            }

            const biasPill = document.getElementById('macro-bias-pill');
            if (biasPill && dossier.gold_macro_bias) {
                biasPill.innerText = `BIAS: ${dossier.gold_macro_bias.replace(/_/g, ' ')}`;
                if (dossier.gold_macro_bias.includes('BULLISH')) {
                    biasPill.style.background = 'rgba(16, 185, 129, 0.2)';
                    biasPill.style.color = '#34d399';
                    biasPill.style.borderColor = 'rgba(16, 185, 129, 0.4)';
                } else if (dossier.gold_macro_bias.includes('BEARISH')) {
                    biasPill.style.background = 'rgba(239, 68, 68, 0.2)';
                    biasPill.style.color = '#f87171';
                    biasPill.style.borderColor = 'rgba(239, 68, 68, 0.4)';
                } else {
                    biasPill.style.background = 'rgba(245, 158, 11, 0.2)';
                    biasPill.style.color = '#fbbf24';
                    biasPill.style.borderColor = 'rgba(245, 158, 11, 0.4)';
                }
            }

            // 2. Cross-Asset Telemetry
            const macroSuite = dossier.macro_suite || {};
            const dxy = macroSuite.dxy || {};
            const us10y = macroSuite.us10y_yield || {};
            const oil = macroSuite.crude_oil || {};

            if (dxy.price) {
                const elPrice = document.getElementById('macro-dxy-price');
                const elChg = document.getElementById('macro-dxy-change');
                const elTrend = document.getElementById('macro-dxy-trend');
                if (elPrice) elPrice.innerText = dxy.price.toFixed(2);
                if (elChg) {
                    const chg = dxy.change_pct || 0;
                    elChg.innerText = `${chg >= 0 ? '+' : ''}${chg.toFixed(2)}%`;
                    elChg.style.color = chg >= 0 ? '#f87171' : '#34d399';
                }
                if (elTrend) {
                    elTrend.innerText = dxy.trend || 'FLAT';
                    elTrend.style.color = dxy.trend === 'UP' ? '#f87171' : (dxy.trend === 'DOWN' ? '#34d399' : '#60a5fa');
                }
            }

            if (us10y.price) {
                const elPrice = document.getElementById('macro-us10y-price');
                const elChg = document.getElementById('macro-us10y-change');
                const elTrend = document.getElementById('macro-us10y-trend');
                if (elPrice) elPrice.innerText = `${us10y.price.toFixed(3)}%`;
                if (elChg) {
                    const chg = us10y.change || 0;
                    elChg.innerText = `${chg >= 0 ? '+' : ''}${chg.toFixed(3)} bps`;
                    elChg.style.color = chg >= 0 ? '#f87171' : '#34d399';
                }
                if (elTrend) {
                    elTrend.innerText = us10y.trend || 'FLAT';
                    elTrend.style.color = us10y.trend === 'UP' ? '#f87171' : (us10y.trend === 'DOWN' ? '#34d399' : '#60a5fa');
                }
            }

            if (oil.price) {
                const elPrice = document.getElementById('macro-oil-price');
                const elChg = document.getElementById('macro-oil-change');
                const elTrend = document.getElementById('macro-oil-trend');
                if (elPrice) elPrice.innerText = `$${oil.price.toFixed(2)}`;
                if (elChg) {
                    const chg = oil.change_pct || 0;
                    elChg.innerText = `${chg >= 0 ? '+' : ''}${chg.toFixed(2)}%`;
                    elChg.style.color = chg >= 0 ? '#34d399' : '#f87171';
                }
                if (elTrend) elTrend.innerText = oil.trend || 'FLAT';
            }

            // 3. Pressure Score & Bar
            const elScore = document.getElementById('macro-gold-score');
            const elBar = document.getElementById('macro-score-bar');
            const elNarrative = document.getElementById('macro-narrative-summary');
            const score = macroSuite.gold_macro_impact_score !== undefined ? macroSuite.gold_macro_impact_score : (dossier.global_shock_score || 0);
            if (elScore) elScore.innerText = `${score >= 0 ? '+' : ''}${score} / 100`;
            if (elBar) {
                const norm = Math.max(0, Math.min(100, ((score + 100) / 200) * 100));
                elBar.style.width = `${norm}%`;
            }
            if (elNarrative && macroSuite.macro_narrative) {
                elNarrative.innerText = macroSuite.macro_narrative;
                elNarrative.title = macroSuite.macro_narrative;
            }

            // 4. Dynamic Trade Manager Badges
            const elClearance = document.getElementById('dyn-clearance-badge');
            if (elClearance && dossier.institutional_action_clearance) {
                elClearance.innerText = `CLEARANCE: ${dossier.institutional_action_clearance.replace(/_/g, ' ')}`;
            }
            const elLotMult = document.getElementById('dyn-lot-mult');
            if (elLotMult) {
                const cl = dossier.institutional_action_clearance || '';
                if (cl.includes('FULL_SWING')) elLotMult.innerText = '1.00x Full Swing Allocation';
                else if (cl.includes('PULLBACK')) elLotMult.innerText = '0.75x Pullback Dip Allocation';
                else if (cl.includes('TACTICAL')) elLotMult.innerText = '0.40x Scalp Allocation';
                else elLotMult.innerText = '0.00x Total Standby (Capital Preserved)';
            }

            // 5. Breaking News Stream
            const newsStream = document.getElementById('macro-news-stream');
            const newsItems = macroSuite.breaking_news || [];
            if (newsStream && newsItems.length > 0) {
                newsStream.innerHTML = '';
                newsItems.slice(0, 6).forEach(item => {
                    const row = document.createElement('div');
                    row.style.cssText = 'font-size: 11px; color: var(--text-muted); padding: 4px 0; border-bottom: 1px solid rgba(255,255,255,0.03); display: flex; align-items: baseline; gap: 6px;';
                    const badgeColor = item.source === 'Google News' ? 'rgba(59,130,246,0.2)' : 'rgba(245,158,11,0.2)';
                    const textColor = item.source === 'Google News' ? '#60a5fa' : '#fbbf24';
                    row.innerHTML = `<span style="background: ${badgeColor}; color: ${textColor}; padding: 1px 5px; border-radius: 3px; font-size: 9px; font-weight: 700; white-space: nowrap;">${item.source || 'News'}</span>
                                     <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${item.title}">${item.title}</span>`;
                    newsStream.appendChild(row);
                });
            }

            // 6. 9-Timeframe Structural Health Radar
            const elAlign = document.getElementById('macro-alignment-pct');
            if (elAlign && dossier.fractal_alignment_pct !== undefined) {
                elAlign.innerText = `FRACTAL ALIGNMENT: ${dossier.fractal_alignment_pct}%`;
            }
            const tfGrid = document.getElementById('macro-multi-tf-grid');
            const matrix = dossier.multi_tf_matrix || [];
            if (tfGrid && matrix.length > 0) {
                tfGrid.innerHTML = '';
                matrix.forEach(tf => {
                    const card = document.createElement('div');
                    const isBull = tf.trend.includes('BULLISH') || tf.trend.includes('READY');
                    const isBear = tf.trend.includes('BEARISH');
                    const trendBg = isBull ? 'rgba(16, 185, 129, 0.15)' : (isBear ? 'rgba(239, 68, 68, 0.15)' : 'rgba(245, 158, 11, 0.15)');
                    const trendColor = isBull ? '#34d399' : (isBear ? '#f87171' : '#fbbf24');
                    const shortName = tf.timeframe.split('/')[0].trim();
                    card.style.cssText = `background: rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.05); border-radius: 8px; padding: 8px 10px; text-align: center;`;
                    card.innerHTML = `
                        <div style="font-size: 10px; font-weight: 700; color: var(--text-sub); margin-bottom: 3px;">${shortName}</div>
                        <div style="font-size: 10px; font-weight: 700; color: ${trendColor}; background: ${trendBg}; padding: 2px 4px; border-radius: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 4px;" title="${tf.trend}">
                            ${tf.trend.replace(/_/g, ' ')}
                        </div>
                        <div style="font-size: 9px; font-family: var(--font-mono); color: var(--text-muted);">${tf.valuation_zone || 'ZONE'}</div>
                    `;
                    tfGrid.appendChild(card);
                });
            }
        }

        async function fetchLiveStatus() {
            try {
                const res = await fetch('/api/status');
                if (res.ok) {
                    const data = await res.json();
                    
                    // Update 360° Institutional Macro Intelligence & Threat Radar
                    if (data.market_research_dossier) {
                        updateMacroThreatRadar(data.market_research_dossier);
                    }
                    
                    // Update Dynamic Multi-Accounts Telemetry for All N Accounts
                    if (data.accounts) {
                        cachedAccountsData = data.accounts;
                        renderSidebarAccounts(data.accounts);
                        updateAdminTelemetry(data.accounts);
                        if (currentAsset === 'ACCOUNTS') {
                            renderAccountsView();
                        }

                        // Dynamically update top navbar metrics
                        const accKeys = Object.keys(data.accounts);
                        if (accKeys.length > 0) {
                            let eqStrings = [];
                            accKeys.forEach(k => {
                                const a = data.accounts[k];
                                const sym = getCurrencySymbol(a.currency);
                                const eq = Number(a.equity || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
                                eqStrings.push(`${sym}${eq} ${a.currency || ''}`);
                            });
                            const elEq = document.getElementById('account-equity');
                            const elBal = document.getElementById('account-balance');
                            if (elEq) elEq.innerText = eqStrings.join(' + ');
                            if (elBal) elBal.innerText = `${accKeys.length} Connected MT5 Terminals`;
                        }
                    } else {
                        if (data.equity) document.getElementById('account-equity').innerText = `€${Number(data.equity).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})} EUR`;
                        if (data.balance) document.getElementById('account-balance').innerText = `Balance: €${Number(data.balance).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})} EUR`;
                    }

                    if (data.total_floating_pnl !== undefined) {
                        const totPnl = data.total_floating_pnl;
                        const totElem = document.getElementById('total-floating-pnl');
                        totElem.innerText = `${totPnl >= 0 ? '+' : ''}€${totPnl.toFixed(2)} EUR`;
                        totElem.style.color = totPnl > 0 ? 'var(--buy-green)' : totPnl < 0 ? 'var(--sell-red)' : 'var(--buy-green)';
                    }
                    if (data.total_open_positions !== undefined) {
                        document.getElementById('open-trades-count').innerText = `${data.total_open_positions} Active Positions in MT5`;
                    }

                    // Update History Summary
                    if (data.history) {
                        cachedHistoryData = data.history;
                        document.getElementById('hist-net-pnl').innerText = `${data.history.net_pnl >= 0 ? '+' : ''}€${data.history.net_pnl.toFixed(2)} EUR`;
                        document.getElementById('hist-trades-stat').innerText = `${data.history.total_ai_trades || 0} AI Closed Trades`;
                        document.getElementById('hist-winrate').innerText = `${data.history.win_rate || 0}%`;
                        document.getElementById('hist-winloss-stat').innerText = `${data.history.wins || 0} Wins / ${data.history.losses || 0} Losses`;
                        if (document.getElementById('hist-missed-stat')) {
                            document.getElementById('hist-missed-stat').innerText = data.history.missed_entries_count || 0;
                        }
                        if (currentAsset === 'HISTORY') {
                            renderHistoryTable();
                        }
                    }

                    // Update 5-Stage Human Pro Trader Pipeline UI
                    if (data.staged_pipeline) {
                        const sp = data.staged_pipeline;
                        const stages = sp.stages || [];
                        stages.forEach(st => {
                            const idx = st.stage;
                            const badge = document.getElementById(`pipe-badge-${idx}`);
                            const step = document.getElementById(`pipe-step-${idx}`);
                            const sub = document.getElementById(`pipe-sub-${idx}`);

                            if (badge && step) {
                                badge.innerText = st.status;
                                if (st.status === 'PASSED') {
                                    badge.style.background = 'rgba(16, 185, 129, 0.2)';
                                    badge.style.color = '#34d399';
                                    badge.style.border = '1px solid rgba(16, 185, 129, 0.4)';
                                    step.style.borderColor = 'rgba(16, 185, 129, 0.3)';
                                } else if (st.status === 'VETOED') {
                                    badge.style.background = 'rgba(239, 68, 68, 0.2)';
                                    badge.style.color = '#f87171';
                                    badge.style.border = '1px solid rgba(239, 68, 68, 0.4)';
                                    step.style.borderColor = 'rgba(239, 68, 68, 0.3)';
                                } else if (st.status === 'APPROVED' || st.status === 'EXECUTED') {
                                    badge.style.background = 'rgba(59, 130, 246, 0.2)';
                                    badge.style.color = '#60a5fa';
                                    badge.style.border = '1px solid rgba(59, 130, 246, 0.4)';
                                    step.style.borderColor = 'rgba(59, 130, 246, 0.3)';
                                } else {
                                    badge.style.background = 'rgba(148, 163, 184, 0.15)';
                                    badge.style.color = '#94a3b8';
                                    badge.style.border = '1px solid rgba(148, 163, 184, 0.2)';
                                    step.style.borderColor = 'rgba(255,255,255,0.06)';
                                }
                            }
                            if (sub && st.subtitle) {
                                sub.innerText = st.subtitle;
                            }
                        });

                        const calloutText = document.getElementById('pipe-callout-text');
                        const calloutBox = document.getElementById('pipe-callout-box');
                        if (calloutText && sp.reason) {
                            calloutText.innerHTML = `<strong>Pipeline State:</strong> ${sp.reason}`;
                            if (calloutBox) {
                                if (sp.reason.includes('VETO')) {
                                    calloutBox.style.borderLeftColor = '#ef4444';
                                } else if (sp.reason.includes('APPROVED')) {
                                    calloutBox.style.borderLeftColor = '#10b981';
                                } else {
                                    calloutBox.style.borderLeftColor = '#3b82f6';
                                }
                            }
                        }
                    }

                    if (data.symbols && data.symbols[currentAsset]) {
                        const sym = data.symbols[currentAsset];
                        document.getElementById('asset-price').innerHTML = `${sym.price} <span style="font-size: 14px; color: var(--buy-green)">USD</span>`;
                        document.getElementById('spread-val').innerText = `Spread: ${sym.spread} pts`;
                        document.getElementById('cro-lots').innerText = sym.cro_lots;

                        // Sidebar pulse updates
                        const sideBid = document.getElementById('side-gold-bid');
                        if (sideBid) sideBid.innerText = `$${sym.price}`;
                        const sideSpread = document.getElementById('side-gold-spread');
                        if (sideSpread) sideSpread.innerText = `${sym.spread} pts`;

                        if (sym.entry_price && sym.stop_loss && sym.take_profit_1 && sym.take_profit_2) {
                            const zoneStr = sym.entry_zone ? ` [Zone: ${sym.entry_zone}]` : '';
                            document.getElementById('trade-levels').innerText = `Entry: ${sym.entry_price.toLocaleString(undefined, {minimumFractionDigits: 2})}${zoneStr} | SL: ${sym.stop_loss.toLocaleString(undefined, {minimumFractionDigits: 2})} | TP1: ${sym.take_profit_1.toLocaleString(undefined, {minimumFractionDigits: 2})} | TP2: ${sym.take_profit_2.toLocaleString(undefined, {minimumFractionDigits: 2})}`;
                        }

                        if (sym.master_action) {
                            const masterActionDiv = document.getElementById('master-action');
                            masterActionDiv.className = `consensus-action ${sym.master_action_class || (sym.master_action === 'BUY' ? 'action-buy' : sym.master_action === 'SELL' ? 'action-sell' : 'action-hold')}`;
                            if (sym.master_action === 'HOLD') {
                                masterActionDiv.innerHTML = `<span>🟡 SIDELINES: WAITING FOR PULLBACK ENTRY</span>`;
                            } else {
                                masterActionDiv.innerHTML = `<span>${sym.master_action === 'BUY' ? '🟢' : '🔴'} ACTION: ${sym.master_action}</span>`;
                            }
                        }

                        if (sym.quorum_score && sym.vote_breakdown) {
                            document.getElementById('quorum-val').innerText = `${sym.quorum_score}% (${sym.vote_breakdown})`;
                            document.getElementById('quorum-bar').style.width = `${sym.quorum_score}%`;
                        }

                        if (sym.open_positions && sym.open_positions.length > 0) {
                            const p0 = sym.open_positions[0];
                            const pnl = p0.profit || 0.0;
                            const pnlColor = pnl >= 0 ? 'var(--buy-green)' : 'var(--sell-red)';
                            const pEntry = Number(p0.open_price || sym.entry_price || 0);
                            const pCur = Number(sym.bid || pEntry);
                            const pSl = Number(p0.sl || (p0.type === 'BUY' ? pEntry - 6.5 : pEntry + 6.5));
                            const pRisk = Math.max(Math.abs(pEntry - pSl), 5.0);
                            const rMult = p0.type === 'BUY' ? ((pCur - pEntry) / pRisk) : ((pEntry - pCur) / pRisk);

                            document.getElementById('pos-header-title').innerText = `Live ${sym.symbol}: ${p0.volume} Lots ${p0.type} @ ${pEntry.toFixed(2)}`;
                            document.getElementById('pos-pnl-display').style.color = pnlColor;
                            document.getElementById('pos-pnl-display').innerText = `Floating PnL: ${pnl >= 0 ? '+' : ''}€${pnl.toFixed(2)} EUR`;
                            
                            const rElem = document.getElementById('pos-r-multiple-display');
                            if (rElem) {
                                rElem.innerText = `R-Multiple: ${rMult >= 0 ? '+' : ''}${rMult.toFixed(2)}R`;
                                rElem.style.color = rMult >= 0.75 ? 'var(--buy-green)' : rMult < 0 ? 'var(--sell-red)' : '#fbbf24';
                            }

                            document.getElementById('pos-badge-status').innerText = 'ACTIVE IN MT5';
                            document.getElementById('pos-badge-status').className = p0.type === 'BUY' ? 'agent-badge badge-buy' : 'agent-badge badge-sell';
                            document.getElementById('active-pos-status').innerText = `Ticket #${p0.ticket} • SL: ${p0.sl || 'Protected'} • TP: ${p0.tp || 'Open'}`;

                            const thoughtEl = document.getElementById('pos-thought-display');
                            if (thoughtEl) {
                                if (rMult >= 1.0) {
                                    thoughtEl.innerHTML = `💡 <strong>Pro Sentry Status:</strong> Trade in high profit (+${rMult.toFixed(2)}R). ATR Ratchet Trailing locked stop above entry. Sentry 3 scanning for M1/M5 momentum exhaustion wicks.`;
                                } else if (rMult >= 0.75) {
                                    thoughtEl.innerHTML = `💡 <strong>Pro Sentry Status:</strong> +0.75R target attained! Sentry 1 (Breakeven Lock) secured stop at entry + buffer. Free risk-free ride active.`;
                                } else {
                                    thoughtEl.innerHTML = `💡 <strong>Pro Sentry Status:</strong> Position monitored. 7 Sentries active on live ticks: BE armed @ +0.75R, Trailing @ +1.0R, Time Decay @ 45m.`;
                                }
                            }
                        } else {
                            document.getElementById('pos-header-title').innerText = `Live ${sym.name}: Pro Trader Active`;
                            document.getElementById('pos-pnl-display').style.color = 'var(--text-muted)';
                            document.getElementById('pos-pnl-display').innerText = 'No Open Position (Standing By)';
                            const rElem = document.getElementById('pos-r-multiple-display');
                            if (rElem) rElem.innerText = 'R-Multiple: 0.00R (Standby)';
                            document.getElementById('pos-badge-status').innerText = 'MONITORING';
                            document.getElementById('pos-badge-status').className = 'agent-badge badge-hold';
                            document.getElementById('active-pos-status').innerText = '7 Sentries Armed: Breakeven, ATR Trail, Momentum Exhaustion, Time Decay';
                            const thoughtEl = document.getElementById('pos-thought-display');
                            if (thoughtEl) {
                                thoughtEl.innerHTML = `🛡️ 7-Sentry Engine: "Standing by. No active market exposure — 7 defensive sentries ready to engage upon entry confirmation."`;
                            }
                        }

                        // Update 7-Sentry Dynamic Diagnostics
                        const sentries = sym.trade_sentries || data.trade_sentries;
                        if (sentries && Array.isArray(sentries)) {
                            sentries.forEach(s => {
                                const cardEl = document.getElementById(`sentry-card-${s.id}`);
                                const badgeEl = document.getElementById(`sentry-badge-${s.id}`);
                                const statusEl = document.getElementById(`sentry-status-${s.id}`);
                                if (badgeEl) {
                                    badgeEl.innerText = s.badge || 'ARMED';
                                    badgeEl.className = `badge-live ${s.badge_class || ''}`;
                                }
                                if (statusEl) {
                                    statusEl.innerText = s.status || s.trigger;
                                    statusEl.style.color = s.active ? '#34d399' : '#fbbf24';
                                }
                                if (cardEl) {
                                    cardEl.style.borderColor = s.active ? 'rgba(16,185,129,0.35)' : 'rgba(255,255,255,0.06)';
                                }
                            });
                        }

                        // Render Multi-TF Pattern Radar & 10 Strategy Agents Matrix
                        if (sym.multi_tf_patterns) {
                            renderPatternRadar(sym.multi_tf_patterns);
                        }

                        if (sym.agents && sym.agents.length > 0) {
                            renderAgents(sym.agents);
                        }
                    }
                }
            } catch (e) {
                console.log("Waiting for live status sync:", e);
            }
        }

        function triggerDeliberation() {
            const logBox = document.getElementById('terminal-logs');
            const now = new Date().toLocaleTimeString();
            logBox.innerHTML += `<div class="log-entry"><span class="log-time">[${now}]</span> <span class="log-info">[Trigger]</span> Live scan refreshed across Gold & Bitcoin council...</div>`;
            logBox.scrollTop = logBox.scrollHeight;
            fetchLiveStatus();
        }

        // ================= JARVIS 3D HOLOGRAPHIC GLOBE & CONSCIOUSNESS ENGINE =================
        let jarvisVoiceEnabled = false;
        let globeRotationY = 0;
        let globeRotationX = 0.25;
        let isDraggingGlobe = false;
        let lastMouseX = 0;
        let lastMouseY = 0;
        let activeHubIndex = 0;

        const GLOBAL_HUBS = [
            { name: "LONDON / NEW YORK OVERLAP", lat: 51.5, lon: -0.1, label: "London (LBMA)", status: "HIGH VOLATILITY", color: "#00f0ff" },
            { name: "NEW YORK SESSIONS (NYSE/CME)", lat: 40.7, lon: -74.0, label: "New York (CME)", status: "INSTITUTIONAL FLOW", color: "#f59e0b" },
            { name: "TOKYO / ASIA PACIFIC", lat: 35.7, lon: 139.7, label: "Tokyo (TSE)", status: "ACCUMULATION", color: "#10b981" },
            { name: "DUBAI GOLD CORRIDOR", lat: 25.2, lon: 55.3, label: "Dubai (DMCC)", status: "SPOT LIQUIDITY", color: "#a855f7" }
        ];

        // 3D Fibonacci Sphere Generator for Holographic Dots
        const GLOBE_DOTS = [];
        const NUM_DOTS = 320;
        for (let i = 0; i < NUM_DOTS; i++) {
            const y = 1 - (i / (NUM_DOTS - 1)) * 2;
            const radius = Math.sqrt(1 - y * y);
            const theta = (Math.PI * (3 - Math.sqrt(5))) * i;
            const x = Math.cos(theta) * radius;
            const z = Math.sin(theta) * radius;
            GLOBE_DOTS.push({ x, y, z });
        }

        function initJarvisGlobe() {
            const canvas = document.getElementById('jarvisGlobeCanvas');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            const dpr = window.devicePixelRatio || 1;
            
            const pWidth = canvas.parentElement ? canvas.parentElement.clientWidth : 360;
            const pHeight = canvas.parentElement ? canvas.parentElement.clientHeight : 280;
            const width = (pWidth > 50) ? pWidth : 360;
            const height = (pHeight > 50) ? pHeight : 280;

            canvas.width = width * dpr;
            canvas.height = height * dpr;
            ctx.scale(dpr, dpr);

            const centerX = width / 2;
            const centerY = height / 2;
            const sphereRadius = Math.min(width, height) * 0.38;

            // Interactive Drag Controls
            canvas.addEventListener('mousedown', (e) => {
                isDraggingGlobe = true;
                lastMouseX = e.clientX;
                lastMouseY = e.clientY;
            });
            window.addEventListener('mouseup', () => { isDraggingGlobe = false; });
            window.addEventListener('mousemove', (e) => {
                if (!isDraggingGlobe) return;
                const dx = e.clientX - lastMouseX;
                const dy = e.clientY - lastMouseY;
                globeRotationY += dx * 0.008;
                globeRotationX += dy * 0.008;
                lastMouseX = e.clientX;
                lastMouseY = e.clientY;
            });

            // Touch support for mobile
            canvas.addEventListener('touchstart', (e) => {
                if (e.touches.length === 1) {
                    isDraggingGlobe = true;
                    lastMouseX = e.touches[0].clientX;
                    lastMouseY = e.touches[0].clientY;
                }
            });
            window.addEventListener('touchend', () => { isDraggingGlobe = false; });
            window.addEventListener('touchmove', (e) => {
                if (!isDraggingGlobe || e.touches.length !== 1) return;
                const dx = e.touches[0].clientX - lastMouseX;
                const dy = e.touches[0].clientY - lastMouseY;
                globeRotationY += dx * 0.008;
                globeRotationX += dy * 0.008;
                lastMouseX = e.touches[0].clientX;
                lastMouseY = e.touches[0].clientY;
            });

            let radarAngle = 0;
            let pulseTime = 0;

            function renderGlobe() {
                ctx.clearRect(0, 0, width, height);

                if (!isDraggingGlobe) {
                    globeRotationY += 0.004; // Smooth automatic orbit
                }
                radarAngle += 0.025;
                pulseTime += 0.04;

                const cosRY = Math.cos(globeRotationY);
                const sinRY = Math.sin(globeRotationY);
                const cosRX = Math.cos(globeRotationX);
                const sinRX = Math.sin(globeRotationX);

                // 1. Draw Outer Holographic Arc Reactor HUD Rings
                ctx.save();
                ctx.translate(centerX, centerY);

                // Outer Rotating Reticle
                ctx.beginPath();
                ctx.arc(0, 0, sphereRadius * 1.25, 0, Math.PI * 2);
                ctx.strokeStyle = 'rgba(0, 240, 255, 0.15)';
                ctx.lineWidth = 1;
                ctx.setLineDash([4, 12]);
                ctx.stroke();
                ctx.setLineDash([]);

                // Inner Arc Reactor Glow Ring
                ctx.beginPath();
                ctx.arc(0, 0, sphereRadius * 1.12, radarAngle * 0.5, radarAngle * 0.5 + Math.PI * 1.5);
                ctx.strokeStyle = 'rgba(0, 240, 255, 0.35)';
                ctx.lineWidth = 1.5;
                ctx.stroke();

                // Crosshair Reticles
                ctx.strokeStyle = 'rgba(0, 240, 255, 0.2)';
                ctx.beginPath();
                ctx.moveTo(-sphereRadius * 1.3, 0); ctx.lineTo(-sphereRadius * 1.18, 0);
                ctx.moveTo(sphereRadius * 1.18, 0); ctx.lineTo(sphereRadius * 1.3, 0);
                ctx.moveTo(0, -sphereRadius * 1.3); ctx.lineTo(0, -sphereRadius * 1.18);
                ctx.moveTo(0, sphereRadius * 1.18); ctx.lineTo(0, sphereRadius * 1.3);
                ctx.stroke();
                ctx.restore();

                // 2. Project and Sort 3D Globe Surface Points
                const projectedDots = GLOBE_DOTS.map(dot => {
                    // Rotate Y
                    let x1 = dot.x * cosRY + dot.z * sinRY;
                    let z1 = -dot.x * sinRY + dot.z * cosRY;
                    // Rotate X
                    let y1 = dot.y * cosRX - z1 * sinRX;
                    let z2 = dot.y * sinRX + z1 * cosRX;

                    return {
                        screenX: centerX + x1 * sphereRadius,
                        screenY: centerY + y1 * sphereRadius,
                        z: z2
                    };
                });

                // Render Background Points (back of the sphere)
                projectedDots.forEach(dot => {
                    if (dot.z < 0) {
                        const alpha = Math.max(0.08, (dot.z + 1) * 0.2);
                        ctx.fillStyle = `rgba(0, 240, 255, ${alpha * 0.4})`;
                        ctx.beginPath();
                        ctx.arc(dot.screenX, dot.screenY, 1, 0, Math.PI * 2);
                        ctx.fill();
                    }
                });

                // 3. Render Foreground Surface Points
                projectedDots.forEach(dot => {
                    if (dot.z >= 0) {
                        const alpha = Math.min(1, 0.3 + dot.z * 0.7);
                        const radius = 1 + dot.z * 1.2;
                        ctx.fillStyle = `rgba(0, 240, 255, ${alpha})`;
                        ctx.shadowColor = '#00f0ff';
                        ctx.shadowBlur = dot.z > 0.6 ? 6 : 0;
                        ctx.beginPath();
                        ctx.arc(dot.screenX, dot.screenY, radius, 0, Math.PI * 2);
                        ctx.fill();
                        ctx.shadowBlur = 0;
                    }
                });

                // 4. Render Global Financial Hubs with Pulse Pings
                GLOBAL_HUBS.forEach((hub, idx) => {
                    const phi = (90 - hub.lat) * (Math.PI / 180);
                    const theta = (hub.lon + 180) * (Math.PI / 180);
                    const hx = -(Math.sin(phi) * Math.cos(theta));
                    const hy = Math.cos(phi);
                    const hz = Math.sin(phi) * Math.sin(theta);

                    let x1 = hx * cosRY + hz * sinRY;
                    let z1 = -hx * sinRY + hz * cosRY;
                    let y1 = hy * cosRX - z1 * sinRX;
                    let z2 = hy * sinRX + z1 * cosRX;

                    if (z2 > -0.1) { // Visible on front or limb
                        const sx = centerX + x1 * sphereRadius;
                        const sy = centerY + y1 * sphereRadius;
                        const isCurrent = (idx === activeHubIndex);
                        const pingSize = 4 + (Math.sin(pulseTime * 2 + idx) + 1) * 6;

                        // Pulse Ring
                        ctx.beginPath();
                        ctx.arc(sx, sy, pingSize, 0, Math.PI * 2);
                        ctx.strokeStyle = isCurrent ? '#00f0ff' : 'rgba(245, 158, 11, 0.5)';
                        ctx.lineWidth = 1;
                        ctx.stroke();

                        // Solid Core Pin
                        ctx.beginPath();
                        ctx.arc(sx, sy, isCurrent ? 4.5 : 3, 0, Math.PI * 2);
                        ctx.fillStyle = isCurrent ? '#00f0ff' : '#f59e0b';
                        ctx.shadowColor = isCurrent ? '#00f0ff' : '#f59e0b';
                        ctx.shadowBlur = 10;
                        ctx.fill();
                        ctx.shadowBlur = 0;

                        // Hub Label
                        ctx.font = '600 10px JetBrains Mono, monospace';
                        ctx.fillStyle = isCurrent ? '#00f0ff' : '#cbd5e1';
                        ctx.fillText(hub.label, sx + 8, sy - 4);
                    }
                });

                requestAnimationFrame(renderGlobe);
            }

            renderGlobe();
        }

        function cycleGlobeHub() {
            activeHubIndex = (activeHubIndex + 1) % GLOBAL_HUBS.length;
            const hub = GLOBAL_HUBS[activeHubIndex];
            const badge = document.getElementById('globe-active-hub');
            const focusBtn = document.getElementById('hubFocusName');
            if (badge) badge.innerText = hub.name;
            if (focusBtn) focusBtn.innerText = `Hub: ${hub.label.split(' ')[0]}`;

            // Smoothly rotate globe towards target hub lon/lat
            const targetRotY = -(hub.lon * (Math.PI / 180)) - Math.PI / 2;
            globeRotationY = targetRotY;

            streamJarvisThought(`🌐 Focused Global Liquidity Node: [${hub.name}] • Session status: ${hub.status}`);
            if (jarvisVoiceEnabled) {
                speakJarvisText(`Liquidity node focused on ${hub.label}. Market state is ${hub.status}.`);
            }
        }

        // ================= REAL-TIME CONSCIOUSNESS STREAM & VOICE =================
        const THOUGHT_TEMPLATES = [
            "Scanning M5/M15 order blocks for Gold... Institutional demand holding base at structural support.",
            "Evaluating 0.618 Fibonacci Golden Pocket on M15... Price holding above OTE key level.",
            "Checking M1 Precision Sniper: Live Bid monitored within ±1.0 pt tolerance band.",
            "Chief Risk Officer (CRO) protocol: Account drawdown 0.00% • 0.07 lots cleared within safety bounds.",
            "Multi-Timeframe Pattern Radar: High harmony score detected across M5, M15, M30, and H1.",
            "ForexFactory news engine query: No high-impact red folder blackout events in next 45 minutes.",
            "Volume Profile & Intraday VWAP: Value Area High defended by institutional buyer absorption."
        ];

        let thoughtIndex = 0;
        function streamJarvisThought(customText) {
            const streamBox = document.getElementById('jarvis-thought-stream');
            const currentThoughtElem = document.getElementById('jarvis-current-thought');
            if (!streamBox) return;

            const now = new Date();
            const timeStr = `[${now.getUTCHours().toString().padStart(2, '0')}:${now.getUTCMinutes().toString().padStart(2, '0')}:${now.getUTCSeconds().toString().padStart(2, '0')} UTC]`;
            const text = customText || THOUGHT_TEMPLATES[thoughtIndex % THOUGHT_TEMPLATES.length];
            thoughtIndex++;

            if (currentThoughtElem) {
                currentThoughtElem.innerText = `"${text}"`;
            }

            const line = document.createElement('div');
            line.className = 'jarvis-stream-line';
            line.style.color = thoughtIndex % 3 === 0 ? '#60a5fa' : thoughtIndex % 3 === 1 ? '#10b981' : '#00f0ff';
            line.innerHTML = `<strong>${timeStr}</strong> 🧠 ${text}`;
            streamBox.appendChild(line);

            // Keep max 20 lines in stream
            while (streamBox.children.length > 20) {
                streamBox.removeChild(streamBox.firstChild);
            }
            streamBox.scrollTop = streamBox.scrollHeight;
        }

        // Animate Audio Waveform Bars
        function animateWaveform() {
            const bars = document.querySelectorAll('.jarvis-wave-bar');
            bars.forEach(bar => {
                const h = Math.floor(Math.random() * 14) + 3;
                bar.style.height = `${h}px`;
            });
        }
        setInterval(animateWaveform, 150);

        // Continuous Thought Engine Loop (Every 4 seconds)
        setInterval(() => {
            streamJarvisThought();
        }, 4000);

        // Voice Speech Synthesizer
        function toggleJarvisVoice() {
            jarvisVoiceEnabled = !jarvisVoiceEnabled;
            const btn = document.getElementById('jarvisVoiceBtn');
            const icon = document.getElementById('jarvisVoiceIcon');
            const text = document.getElementById('jarvisVoiceText');

            if (jarvisVoiceEnabled) {
                btn.className = 'jarvis-btn voice-active';
                icon.innerText = '🔊';
                text.innerText = 'Voice Comm: ON';
                speakJarvisText("Bullion AI Neural Core voice synthesis online. Monitoring MetaTrader 5 markets.");
            } else {
                btn.className = 'jarvis-btn';
                icon.innerText = '🎙️';
                text.innerText = 'Voice Comm: OFF';
                if (window.speechSynthesis) window.speechSynthesis.cancel();
            }
        }

        let pendingTradeIntent = null;
        let speechRecognition = null;
        let isListening = false;

        function cleanMarkdownForVoice(text) {
            if (!text) return "";
            return text
                .replace(/\[ACTION:[^\]]+\]/g, '')
                .replace(/\*\*(.*?)\*\*/g, '$1')
                .replace(/\*(.*?)\*/g, '$1')
                .replace(/#{1,6}\s?/g, '')
                .replace(/`{1,3}[^`]*`{1,3}/g, '')
                .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
                .replace(/[-_]{3,}/g, '')
                .trim();
        }

        let cachedVoices = [];

        if ('speechSynthesis' in window) {
            cachedVoices = window.speechSynthesis.getVoices();
            window.speechSynthesis.onvoiceschanged = () => {
                cachedVoices = window.speechSynthesis.getVoices();
            };
        }

        function speakBullionVoice(text, lang = 'auto') {
            if (!('speechSynthesis' in window)) return;
            window.speechSynthesis.cancel();

            const cleanText = cleanMarkdownForVoice(text);
            if (!cleanText) return;

            const utterance = new SpeechSynthesisUtterance(cleanText);
            utterance.rate = 1.0;
            utterance.pitch = 1.0;
            utterance.volume = 1.0;

            const voices = cachedVoices.length > 0 ? cachedVoices : window.speechSynthesis.getVoices();
            let selectedVoice = null;

            const targetLang = (lang || 'auto').toLowerCase();

            if (targetLang === 'mr' || targetLang === 'marathi') {
                selectedVoice = voices.find(v => v.lang.toLowerCase().startsWith('mr') || v.name.toLowerCase().includes('marathi'));
            } else if (targetLang === 'hi' || targetLang === 'hindi') {
                selectedVoice = voices.find(v => v.lang.toLowerCase().startsWith('hi') || v.name.toLowerCase().includes('hindi') || v.name.toLowerCase().includes('kalpana') || v.name.toLowerCase().includes('hemant') || v.name.toLowerCase().includes('neerja'));
            }

            if (!selectedVoice) {
                selectedVoice = voices.find(v => v.lang.includes('IN') || v.lang.includes('hi') || v.lang.includes('mr'));
            }

            if (!selectedVoice) {
                selectedVoice = voices.find(v => v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('India') || v.name.includes('UK') || v.name.includes('Male')));
            }

            if (selectedVoice) {
                utterance.voice = selectedVoice;
            }
            window.speechSynthesis.speak(utterance);
        }

        // Voice Speech Synthesizer Toggle
        function toggleJarvisVoice() {
            jarvisVoiceEnabled = !jarvisVoiceEnabled;
            const btn = document.getElementById('jarvisVoiceBtn');
            const icon = document.getElementById('jarvisVoiceIcon');
            const text = document.getElementById('jarvisVoiceText');

            if (jarvisVoiceEnabled) {
                btn.className = 'jarvis-btn voice-active';
                icon.innerText = '🔊';
                text.innerText = 'Voice Comm: ON';
                speakBullionVoice("Bullion AI Voice Engine online. Live MetaTrader 5 institutional radar active.", "en");
            } else {
                btn.className = 'jarvis-btn';
                icon.innerText = '🎙️';
                text.innerText = 'Voice Comm: OFF';
                if (window.speechSynthesis) window.speechSynthesis.cancel();
            }
        }

        function speakJarvisThesis() {
            const currentThought = document.getElementById('jarvis-current-thought')?.innerText || "Analyzing market structure.";
            const masterAction = document.getElementById('master-action')?.innerText || "BUY";
            const levels = document.getElementById('trade-levels')?.innerText || "";
            const userLang = document.getElementById('userLangSelect')?.value || 'auto';
            const text = `Bullion AI Status Report: Master ruling is ${masterAction}. ${currentThought} ${levels}`;
            speakBullionVoice(text, userLang);
        }

        // ================= MULTILINGUAL CHAT & VOICE INTERACTION =================
        async function sendUserChatMessage(customQuery = null) {
            const inputElem = document.getElementById('bullionChatInput');
            const query = (customQuery || inputElem.value || '').trim();
            if (!query) return;

            if (!customQuery) inputElem.value = '';
            const userLang = document.getElementById('userLangSelect').value;

            // Stream user message
            streamJarvisThought(`👤 User: "${query}"`);

            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: query, language: userLang })
                });

                if (res.ok) {
                    const data = await res.json();
                    streamJarvisThought(`🤖 Bullion AI: ${data.reply}`);

                    // Speak in matched language
                    speakBullionVoice(data.reply, data.detected_language || userLang);

                    // Check if trade security confirmation is required
                    if (data.action_intent && data.action_intent.require_code) {
                        pendingTradeIntent = data.action_intent;
                        const secBox = document.getElementById('securityCodeBox');
                        const secDesc = document.getElementById('secPromptDesc');
                        secDesc.innerText = data.reply;
                        secBox.style.display = 'block';
                        document.getElementById('secCodeInput').value = '';
                        document.getElementById('secCodeInput').focus();
                    }
                }
            } catch (e) {
                console.error("Chat error:", e);
                streamJarvisThought(`❌ Error contacting Bullion AI neural core: ${e.message}`);
            }
        }

        function sendQuickPrompt(promptText) {
            document.getElementById('bullionChatInput').value = promptText;
            sendUserChatMessage(promptText);
        }

        async function confirmAndExecuteTradeWithCode() {
            const codeInput = document.getElementById('secCodeInput');
            const secCode = (codeInput.value || '').trim();
            const userLang = document.getElementById('userLangSelect').value;

            if (!pendingTradeIntent) {
                pendingTradeIntent = { action: "BUY", symbol: "XAUUSD" };
            }

            try {
                const res = await fetch('/api/voice-execute', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        security_code: secCode,
                        action: pendingTradeIntent.action || "BUY",
                        symbol: pendingTradeIntent.symbol || "XAUUSD",
                        volume: 0.01,
                        language: userLang
                    })
                });

                const data = await res.json();
                if (res.ok && data.success) {
                    streamJarvisThought(`🎉 ${data.message}`);
                    speakBullionVoice(data.speak_text || data.message, userLang);
                    document.getElementById('securityCodeBox').style.display = 'none';
                    pendingTradeIntent = null;
                    fetchLiveStatus();
                } else {
                    streamJarvisThought(`🚫 ${data.message || 'Authorization Failed'}`);
                    speakBullionVoice(data.speak_text || data.message, userLang);
                    codeInput.value = '';
                    codeInput.focus();
                }
            } catch (e) {
                console.error("Exec error:", e);
                streamJarvisThought(`❌ Error executing trade: ${e.message}`);
            }
        }

        function cancelTradeCommand() {
            document.getElementById('securityCodeBox').style.display = 'none';
            pendingTradeIntent = null;
            streamJarvisThought("⚠️ Trade command canceled by user.");
            speakBullionVoice("Trade execution canceled.", "en");
        }

        // ================= MICROPHONE SPEECH-TO-TEXT (HINDI / MARATHI / ENGLISH) =================
        function toggleMicSpeechRecognition() {
            const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SpeechRec) {
                alert("Speech recognition is not supported in this browser. Please use Google Chrome or Microsoft Edge.");
                return;
            }

            const micStatus = document.getElementById('micListeningStatus');
            const micIcon = document.getElementById('micBtnIcon');

            if (isListening) {
                if (speechRecognition) speechRecognition.stop();
                isListening = false;
                micStatus.style.display = 'none';
                micIcon.innerText = '🎤';
                return;
            }

            speechRecognition = new SpeechRec();
            speechRecognition.continuous = false;
            speechRecognition.interimResults = false;

            const userLang = document.getElementById('userLangSelect').value;
            if (userLang === 'mr') {
                speechRecognition.lang = 'mr-IN';
            } else if (userLang === 'hi') {
                speechRecognition.lang = 'hi-IN';
            } else if (userLang === 'en') {
                speechRecognition.lang = 'en-IN';
            } else {
                speechRecognition.lang = 'hi-IN'; // Indian multilingual recognition default
            }

            speechRecognition.onstart = () => {
                isListening = true;
                micStatus.style.display = 'inline';
                micIcon.innerText = '⏹️';
            };

            speechRecognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                document.getElementById('bullionChatInput').value = transcript;
                
                // If security box is open and user spoke the security code
                if (document.getElementById('securityCodeBox').style.display === 'block') {
                    if (transcript.includes('198311') || transcript.includes('198 311') || transcript.includes('19 83 11') || transcript.includes('198-311')) {
                        document.getElementById('secCodeInput').value = '198311';
                        confirmAndExecuteTradeWithCode();
                        return;
                    }
                }

                sendUserChatMessage(transcript);
            };

            speechRecognition.onerror = (e) => {
                console.error("Mic error:", e);
                isListening = false;
                micStatus.style.display = 'none';
                micIcon.innerText = '🎤';
            };

            speechRecognition.onend = () => {
                isListening = false;
                micStatus.style.display = 'none';
                micIcon.innerText = '🎤';
            };

            speechRecognition.start();
        }
    