/**
 * Smart Home AI Decision Assistant
 * 
 * Main Application Logic for AI Discovery, Recommendations, Analytics & Comparison
 */

(function() {
    'use strict';

    // ─── STATE MANAGEMENT ─────────────────────────────────────
    const state = {
        lastResults: [],
        aiAnalysis: null,
        favorites: JSON.parse(localStorage.getItem('sh_favorites') || '[]'),
        compareIndices: [],
        activePage: 'home',
        auth: {
            isAuthenticated: false,
            user: null,
            guestId: null
        },
        chatHistory: []
    };

    // ─── SELECTORS ───────────────────────────────────────────
    const $ = (s) => document.querySelector(s);
    const $$ = (s) => document.querySelectorAll(s);

    function renderFeatureChips(features) {
        const items = (features || []).filter(Boolean).slice(0, 6);
        if (!items.length) {
            return '<div class="feature-chip-row"><span class="feature-chip">Feature details available</span></div>';
        }
        return `<div class="feature-chip-row">${items.map((feature) => `<span class="feature-chip">${feature}</span>`).join('')}</div>`;
    }

    // ─── INITIALIZATION ───────────────────────────────────────
    document.addEventListener('DOMContentLoaded', () => {
        setupEventListeners();
        updateFavCount();
        initializeUserSession();
    });

    async function initializeUserSession() {
        setAuthLoading(true);
        await fetchAuthState();
        await loadChatHistory();
        setAuthLoading(false);
    }

    function setAuthLoading(isLoading) {
        const loading = $('#authLoading');
        if (!loading) return;
        loading.style.display = isLoading ? 'inline-flex' : 'none';
    }

    async function fetchAuthState() {
        try {
            const resp = await fetch('/auth/me');
            if (!resp.ok) return;
            const data = await resp.json();
            state.auth.isAuthenticated = !!(data.logged_in || data.is_authenticated);
            state.auth.user = data.user || null;
            state.auth.guestId = data.guest_id || null;
            if (!state.auth.isAuthenticated && state.auth.guestId) {
                localStorage.setItem('guest_id', state.auth.guestId);
            }
            renderAuthState();
        } catch (e) {
            console.error('Failed to fetch auth state', e);
        }
    }

    function renderAuthState() {
        const loginBtn = $('#loginBtn');
        const profileDropdown = $('#profileDropdown');
        const userName = $('#userName');
        const userStatus = $('#userStatus');
        const userAvatar = $('#userAvatar');
        const navAvatar = $('#navbarProfileAvatar');
        const navName = $('#navbarProfileName');
        const menuAvatar = $('#dropdownProfileAvatar');
        const menuName = $('#dropdownProfileName');
        const menuEmail = $('#dropdownProfileEmail');

        if (state.auth.isAuthenticated && state.auth.user) {
            if (loginBtn) loginBtn.style.display = 'none';
            if (profileDropdown) profileDropdown.style.display = 'inline-block';
            if (userName) userName.textContent = state.auth.user.name || 'Signed In User';
            if (userStatus) userStatus.textContent = state.auth.user.email || 'Authenticated';
            if (navName) navName.textContent = state.auth.user.name || 'User';
            if (menuName) menuName.textContent = state.auth.user.name || 'User';
            if (menuEmail) menuEmail.textContent = state.auth.user.email || '';

            const avatarText = (state.auth.user.name || 'U').trim().slice(0, 2).toUpperCase();
            if (userAvatar) {
                userAvatar.textContent = avatarText;
                if (state.auth.user.profile_pic) {
                    userAvatar.style.backgroundImage = `url('${state.auth.user.profile_pic}')`;
                    userAvatar.style.backgroundSize = 'cover';
                    userAvatar.style.backgroundPosition = 'center';
                    userAvatar.style.color = 'transparent';
                }
            }

            [navAvatar, menuAvatar].forEach((avatarNode) => {
                if (!avatarNode) return;
                avatarNode.textContent = avatarText;
                if (state.auth.user.profile_pic) {
                    avatarNode.style.backgroundImage = `url('${state.auth.user.profile_pic}')`;
                    avatarNode.style.backgroundSize = 'cover';
                    avatarNode.style.backgroundPosition = 'center';
                    avatarNode.style.color = 'transparent';
                }
            });
            return;
        }

        if (loginBtn) loginBtn.style.display = 'inline-flex';
        if (profileDropdown) profileDropdown.style.display = 'none';
        if (userName) userName.textContent = 'Guest User';
        if (userStatus) userStatus.textContent = 'Guest Mode';
        if (userAvatar) {
            userAvatar.textContent = 'AI';
            userAvatar.style.backgroundImage = '';
            userAvatar.style.color = '#fff';
        }

        [navAvatar, menuAvatar].forEach((avatarNode) => {
            if (!avatarNode) return;
            avatarNode.textContent = 'AI';
            avatarNode.style.backgroundImage = '';
            avatarNode.style.color = '#fff';
        });
        if (navName) navName.textContent = 'Guest';
        if (menuName) menuName.textContent = 'Guest User';
        if (menuEmail) menuEmail.textContent = 'Guest Mode';
    }

    async function loadChatHistory() {
        try {
            const resp = await fetch('/chat/history?limit=15');
            if (!resp.ok) return;
            const data = await resp.json();
            state.chatHistory = data.items || [];
            renderChatHistory();
        } catch (e) {
            console.error('Failed to load chat history', e);
        }
    }

    function renderChatHistory() {
        const container = $('#chatHistoryList');
        if (!container) return;

        if (!state.chatHistory.length) {
            container.innerHTML = '<div class="history-empty">No chat history yet.</div>';
            return;
        }

        container.innerHTML = state.chatHistory.map(item => {
            const ts = item.timestamp ? new Date(item.timestamp).toLocaleString() : 'Unknown time';
            const summary = item.summary || 'Saved smart-home recommendation';
            return `
                <button class="history-item" onclick="loadHistoryItem(${item.id})">
                    <div class="history-query">${escapeHtml(item.query || 'Untitled query')}</div>
                    <div class="history-summary">${escapeHtml(summary)}</div>
                    <div class="history-time">${escapeHtml(ts)}</div>
                </button>
            `;
        }).join('');
    }

    window.loadHistoryItem = async function(entryId) {
        try {
            const resp = await fetch(`/chat/history/${entryId}`);
            if (!resp.ok) throw new Error('Unable to load history item');
            const item = await resp.json();
            const payload = item.response || {};

            state.lastResults = payload.recommended_products || [];
            state.aiAnalysis = payload.ai_analysis || null;

            if ($('#aiQuery')) {
                $('#aiQuery').value = item.query || '';
            }

            if (state.aiAnalysis) {
                $('#intentStream').innerHTML = '';
                popIntentTags(state.aiAnalysis);
                renderAIIntent(state.aiAnalysis);
            }
            renderProductGrid(state.lastResults);
            updateRecommendationsDisplay();
            showPage('recommendations');
            showToast('Loaded saved recommendation', 'success');
        } catch (e) {
            showToast(e.message, 'error');
        }
    };

    function setupEventListeners() {
        // AI Submission
        const aiSubmit = $('#aiSubmit');
        const aiQuery = $('#aiQuery');
        if (aiSubmit && aiQuery) {
            aiSubmit.onclick = performAISearch;
            aiQuery.onkeypress = (e) => {
                if (e.key === 'Enter') performAISearch();
            };
        }
    }

    // ─── VOICE SEARCH FUNCTIONALITY ──────────────────────────
    let recognition = null;
    let isListening = false;

    function initVoiceRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            showToast('Speech Recognition not supported in your browser.', 'error');
            return false;
        }

        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.language = 'en-IN'; // Support Indian English

        recognition.onstart = () => {
            isListening = true;
            const voiceBtn = $('#aiVoice');
            if (voiceBtn) voiceBtn.classList.add('recording');
            const voiceWaves = $('#voiceWaves');
            if (voiceWaves) voiceWaves.style.display = 'block';
            const status = $('#voiceStatus');
            if (status) {
                status.innerHTML = '<i class="fas fa-microphone"></i> Listening...';
                status.style.display = 'flex';
            }
        };

        recognition.onresult = (event) => {
            let interimTranscript = '';
            let finalTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript + ' ';
                } else {
                    interimTranscript += transcript;
                }
            }

            const aiQuery = $('#aiQuery');
            if (aiQuery) {
                aiQuery.value = finalTranscript || interimTranscript;
            }
        };

        recognition.onerror = (event) => {
            let errorMsg = 'Voice recognition error.';
            if (event.error === 'no-speech') {
                errorMsg = 'No speech detected. Please try again.';
            } else if (event.error === 'network') {
                errorMsg = 'Network error. Check your connection.';
            }
            showToast(errorMsg, 'error');
            stopVoiceSearch();
        };

        recognition.onend = () => {
            stopVoiceSearch();
        };

        return true;
    }

    window.toggleVoiceSearch = function() {
        if (!recognition) {
            if (!initVoiceRecognition()) return;
        }

        if (isListening) {
            stopVoiceSearch();
        } else {
            startVoiceSearch();
        }
    };

    function startVoiceSearch() {
        if (recognition && !isListening) {
            const aiQuery = $('#aiQuery');
            if (aiQuery) aiQuery.value = '';
            recognition.start();
        }
    }

    function stopVoiceSearch() {
        if (recognition && isListening) {
            recognition.stop();
            isListening = false;
            const voiceBtn = $('#aiVoice');
            if (voiceBtn) voiceBtn.classList.remove('recording');
            const voiceWaves = $('#voiceWaves');
            if (voiceWaves) voiceWaves.style.display = 'none';
            const status = $('#voiceStatus');
            if (status) {
                status.innerHTML = '<i class="fas fa-check-circle"></i> Voice captured';
                setTimeout(() => {
                    status.style.display = 'none';
                }, 2000);
            }
        }
    }

    // ─── NAVIGATION ───────────────────────────────────────────
    function showPage(pageId) {
        state.activePage = pageId;
        
        // Update Sections
        $$('.section-page').forEach(p => p.classList.remove('active'));
        const target = $('#' + pageId + 'Page');
        if (target) target.classList.add('active');
        
        // Update Links (Sidebar Support)
        $$('.sidebar-link').forEach(l => l.classList.remove('active'));
        const activeLink = $('#link-' + pageId);
        if (activeLink) activeLink.classList.add('active');
        
        window.scrollTo({top: 0, behavior: 'smooth'});
        
        // Page specific logic
        if (pageId === 'analytics') renderAnalytics();
        if (pageId === 'compare') renderComparePage();
        if (pageId === 'recommendations') updateRecommendationsDisplay();
    }

    window.showPage = showPage;

    function updateRecommendationsDisplay() {
        // Copy products to recommendations section
        const recContainer = $('#recommendationsContent');
        if (recContainer && state.lastResults.length > 0) {
            recContainer.className = 'product-grid-modern';
            recContainer.innerHTML = state.lastResults.map((p, i) => {
                const score = parseInt(p.match_score) || 0;
                const isFavorite = state.favorites.some(f => f.name === p.name);
                const isComparing = state.compareIndices.includes(i);
                const isExpertPick = i === 0;

                return `
                    <div class="product-card-modern">
                        ${isExpertPick ? '<span class="expert-badge"><i class="fas fa-crown me-1"></i>Expert Pick</span>' : ''}
                        <div class="product-image">
                            ${p.image_url ? `<img src="${p.image_url}" alt="${p.name}">` : '<i class="fas fa-box fa-3x" style="color: var(--text-muted)"></i>'}
                            <div class="match-score-ring">
                                <div class="score-text">
                                    <div class="score-number">${score}</div>
                                    <div class="score-label">Match</div>
                                </div>
                            </div>
                        </div>
                        <div class="product-details">
                            <div class="product-title">${p.name}</div>
                            <div class="product-price">${formatPrice(p.price_inr)}</div>
                            <div class="product-rating">
                                <span class="stars"><i class="fas fa-star"></i> ${(p.rating || 4.5).toFixed(1)}</span>
                                <span>${p.review_count || 100} reviews</span>
                            </div>
                            ${renderFeatureChips(p.features)}
                            <p class="product-reason">${p.ai_reason || p.reason || 'Smart home device recommendation'}</p>
                            
                            <div class="product-actions">
                                <button class="action-btn" onclick="openDetail(${i})" title="AI Analysis">
                                    <i class="fas fa-microchip"></i> AI Analysis
                                </button>
                                <button class="action-btn" onclick="toggleFavorite(${i})" title="${isFavorite ? 'Remove from favorites' : 'Add to favorites'}">
                                    <i class="fas fa-heart" style="color: ${isFavorite ? '#EF4444' : 'currentColor'}"></i>
                                </button>
                                <button class="action-btn" onclick="toggleCompare(${i})" title="Compare" style="background: ${isComparing ? 'rgba(99, 102, 241, 0.3)' : 'rgba(99, 102, 241, 0.1)'}">
                                    <i class="fas fa-exchange-alt"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }
    }

    // ─── AI SEARCH FLOW ──────────────────────────────────────
    async function performAISearch() {
        const query = $('#aiQuery').value.trim();
        if (!query) {
            showToast('Please describe what appliance you need.', 'error');
            return;
        }

        // Logic for Unlimited Budget tag
        const aiInput = $('#aiQuery');
        if (query.toLowerCase().includes('unlimited') || query.toLowerCase().includes('no budget')) {
            aiInput.classList.add('unlimited-tag');
        } else {
            aiInput.classList.remove('unlimited-tag');
        }

        showSkeletons();
        $('#aiAnalysisResults').style.display = 'none';
        $('#intentStream').innerHTML = '';

        try {
            const resp = await fetch('/advisor', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query })
            });

            if (!resp.ok) {
                 let errMsg = 'AI analysis failed.';
                 try {
                     const err = await resp.json();
                     errMsg = err.detail || err.message || errMsg;
                 } catch (e) {
                     // If response is not JSON, use status text
                     errMsg = resp.statusText || errMsg;
                 }
                 throw new Error(errMsg);
            }

            const data = await resp.json();
            state.lastResults = data.recommended_products || [];
            state.aiAnalysis = data.ai_analysis || {};

            // Pop Intent Tags
            popIntentTags(state.aiAnalysis);

            renderAIIntent(state.aiAnalysis);
            renderProductGrid(state.lastResults);
            
            // Auto-move to recommendations after a delay to let user see intent extraction
            setTimeout(() => {
                updateRecommendationsDisplay();
                showPage('recommendations');
                loadChatHistory();
                if (state.lastResults.length > 0) {
                    showToast(`AI found ${state.lastResults.length} matches!`, 'success');
                }
            }, 2500);

        } catch (e) {
            hideSkeletons();
            // Check if it's an off-topic error
            if (e.message.toLowerCase().includes('smart home') && e.message.toLowerCase().includes('unrelated')) {
                // Show off-topic card below search bar
                $('#offTopicCard').style.display = 'block';
                // Scroll to show the card
                setTimeout(() => {
                    $('#offTopicCard').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }, 100);
            } else {
                showToast(e.message, 'error');
            }
        } finally {
            hideSkeletons();
        }
    }

    function showSkeletons() {
        const loadingOverlay = $('#loadingOverlay');
        if (loadingOverlay) {
            loadingOverlay.style.display = 'block';
        }
    }

    function hideSkeletons() {
        const loadingOverlay = $('#loadingOverlay');
        if (loadingOverlay) {
            loadingOverlay.style.display = 'none';
        }
    }

    function popIntentTags(ai) {
        const tags = [];
        if (ai.category) tags.push(`<i class="fas fa-tag me-1"></i>${ai.category}`);
        if (ai.budget) tags.push(`<i class="fas fa-coins me-1"></i>₹${ai.budget}`);
        else tags.push(`<i class="fas fa-infinity me-1"></i>Unlimited`);
        
        if (ai.energy_efficiency) tags.push(`<i class="fas fa-leaf me-1"></i>${ai.energy_efficiency}`);
        (ai.preferences || []).forEach(p => tags.push(`<i class="fas fa-check me-1"></i>${p}`));

        const container = $('#intentStream');
        tags.forEach((tagHtml, i) => {
            setTimeout(() => {
                const div = document.createElement('div');
                div.className = 'intent-tag';
                div.innerHTML = tagHtml;
                container.appendChild(div);
            }, i * 400);
        });
    }

    // ─── RENDERING ────────────────────────────────────────────
    function renderAIIntent(ai) {
        const container = $('#aiAnalysisContent');
        if (!container) return;
        
        $('#aiAnalysisResults').style.display = 'block';
        
        container.innerHTML = `
            <div class="col-md-3 mb-3">
                <div class="text-muted small">Category</div>
                <div class="fw-700">${ai.category || 'Any'}</div>
            </div>
            <div class="col-md-3 mb-3">
                <div class="text-muted small">Budget</div>
                <div class="fw-700 font-serif">${formatPrice(ai.budget) || 'Any'}</div>
            </div>
            <div class="col-md-3 mb-3">
                <div class="text-muted small">Efficiency</div>
                <div class="fw-700 text-success"><i class="fas fa-leaf me-1"></i>${ai.energy_efficiency || 'Standard'}</div>
            </div>
            <div class="col-md-3 mb-3">
                <div class="text-muted small">Key Requirements</div>
                <div class="fw-700">${(ai.preferences || []).join(', ') || 'Smart features'}</div>
            </div>
        `;
    }

    function renderProductGrid(products) {
        const grid = $('#productGrid');
        if (!grid) return;

        if (products.length === 0) {
            grid.innerHTML = `
                <div class="cinematic-empty w-100">
                    <img src="/static/assets/empty_home.jpg" class="empty-bg-image" alt="Empty Home">
                    <div class="position-relative">
                        <i class="fas fa-sparkles fa-4x mb-4 text-accent opacity-75"></i>
                        <h2 class="fw-800">No Perfect Match Found</h2>
                        <p class="text-secondary mb-4 mx-auto" style="max-width: 500px;">
                            We couldn't find a perfect match, but let's try adjusting your requirements.
                        </p>
                        <button class="btn btn-hero btn-hero-primary" onclick="showPage('assistant')">Adjust Parameters</button>
                    </div>
                </div>
            `;
            return;
        }

        grid.innerHTML = products.map((p, i) => {
            const score = parseInt(p.match_score) || 0;
            const isFavorite = state.favorites.some(f => f.name === p.name);
            const isComparing = state.compareIndices.includes(i);
            const isExpertPick = i === 0;

            return `
                <div class="product-card-modern">
                    ${isExpertPick ? '<span class="expert-badge"><i class="fas fa-crown me-1"></i>Expert Pick</span>' : ''}
                    <div class="product-image">
                        ${p.image_url ? `<img src="${p.image_url}" alt="${p.name}">` : '<i class="fas fa-box fa-3x" style="color: var(--text-muted)"></i>'}
                        <div class="match-score-ring">
                            <div class="score-text">
                                <div class="score-number">${score}</div>
                                <div class="score-label">Match</div>
                            </div>
                        </div>
                    </div>
                    <div class="product-details">
                        <div class="product-title">${p.name}</div>
                        <div class="product-price">${formatPrice(p.price_inr)}</div>
                        <div class="product-rating">
                            <span class="stars"><i class="fas fa-star"></i> ${(p.rating || 4.5).toFixed(1)}</span>
                            <span>${p.review_count || 100} reviews</span>
                        </div>
                        ${renderFeatureChips(p.features)}
                        <p class="product-reason">${p.ai_reason || p.reason || 'Smart home device recommendation'}</p>
                        
                        <div class="product-actions">
                            <button class="action-btn" onclick="openDetail(${i})" title="AI Analysis">
                                <i class="fas fa-microchip"></i> AI Analysis
                            </button>
                            <button class="action-btn" onclick="toggleFavorite(${i})" title="${isFavorite ? 'Remove from favorites' : 'Add to favorites'}">
                                <i class="fas fa-heart" style="color: ${isFavorite ? '#EF4444' : 'currentColor'}"></i>
                            </button>
                            <button class="action-btn" onclick="toggleCompare(${i})" title="Compare" style="background: ${isComparing ? 'rgba(99, 102, 241, 0.3)' : 'rgba(99, 102, 241, 0.1)'}">
                                <i class="fas fa-exchange-alt"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        // Update recommendations section with found count
        const foundCount = $('#foundCount');
        if (foundCount) {
            foundCount.textContent = `Found ${products.length} Optimized Matches`;
        }
        
        $('#resultMeta').textContent = '';
    }

    // ─── ANALYTICS ───────────────────────────────────────────
    let currentCharts = {};
    function renderAnalytics() {
        if (state.lastResults.length === 0) return;
        
        const labels = state.lastResults.map(p => p.name.split(' ').slice(0, 3).join(' '));
        const scores = state.lastResults.map(p => parseInt(p.match_score) || 0);
        const prices = state.lastResults.map(p => parseInt(p.price_inr) || 0);

        if (currentCharts.score) currentCharts.score.destroy();
        if (currentCharts.price) currentCharts.price.destroy();

        // Match Scores Chart
        const scoreCtx = document.createElement('canvas');
        $('#featureDistChart').innerHTML = '';
        $('#featureDistChart').appendChild(scoreCtx);
        currentCharts.score = new Chart(scoreCtx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Match Confidence (%)',
                    data: scores,
                    backgroundColor: 'rgba(99, 102, 241, 0.7)',
                    borderRadius: 12,
                }]
            },
            options: { 
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { 
                    y: { beginAtZero: true, max: 100, border: {display: false} },
                    x: { border: {display: false}, grid: {display: false} }
                }
            }
        });

        // Price Trend
        const priceCtx = document.createElement('canvas');
        $('#priceDistChart').innerHTML = '';
        $('#priceDistChart').appendChild(priceCtx);
        currentCharts.price = new Chart(priceCtx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Unit Price',
                    data: prices,
                    borderColor: '#A855F7',
                    borderWidth: 4,
                    fill: true,
                    backgroundColor: 'rgba(168, 85, 247, 0.05)',
                    pointRadius: 6,
                    pointBackgroundColor: '#fff',
                    tension: 0.4
                }]
            },
            options: { 
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { 
                    y: { border: {display: false} },
                    x: { border: {display: false}, grid: {display: false} }
                }
            }
        });
    }

    // ─── COMPARISON ENGINE ───────────────────────────────────
    window.toggleCompare = function(index) {
        if (state.compareIndices.includes(index)) {
            state.compareIndices = state.compareIndices.filter(i => i !== index);
        } else {
            if (state.compareIndices.length >= 6) {
                showToast('Maximum 6 products for comparison', 'warning');
                return;
            }
            state.compareIndices.push(index);
        }
        renderProductGrid(state.lastResults);
        updateRecommendationsDisplay();
        if (state.activePage === 'compare') renderComparePage();
    };

    function renderComparePage() {
        const table = $('#compareTableContainer');
        const empty = $('#compareEmptyState');
        if (state.compareIndices.length < 2) {
            table.style.display = 'none';
            empty.style.display = 'block';
            return;
        }

        empty.style.display = 'none';
        table.style.display = 'block';

        const items = state.compareIndices.map(idx => state.lastResults[idx]);
        
        // Find winners for highlighting
        const minPrice = Math.min(...items.map(p => p.price_inr || Infinity));
        const maxScore = Math.max(...items.map(p => parseInt(p.match_score) || 0));

        // Build Header
        let hHtml = '<tr><th style="width:240px">Specification Attributes</th>';
        items.forEach(p => hHtml += `<th class="text-center"><div class="fw-800 text-truncate mx-auto" style="max-width:180px">${p.name}</div></th>`);
        hHtml += '</tr>';
        $('#compareHeader').innerHTML = hHtml;

        // Build Rows
        let bHtml = `
            <tr class="compare-row">
                <td class="fw-700">Market Price</td>
                ${items.map(p => `<td class="text-center fw-800 ${p.price_inr === minPrice ? 'compare-win' : ''}">${formatPrice(p.price_inr)}</td>`).join('')}
            </tr>
            <tr class="compare-row">
                <td class="fw-700">AI Alignment Score</td>
                ${items.map(p => `<td class="text-center fw-800 ${parseInt(p.match_score) === maxScore ? 'compare-win' : ''}">${p.match_score}% Match</td>`).join('')}
            </tr>
             <tr class="compare-row">
                <td class="fw-700">Key Features</td>
                ${items.map(p => `<td><div class="small">${(p.features || []).slice(0, 4).join(', ') || 'N/A'}</div></td>`).join('')}
            </tr>
            <tr class="compare-row">
                <td class="fw-700">Expert Verdict</td>
                ${items.map(p => `<td class="small text-secondary fw-500">${p.ai_reason || p.reason || 'Optimal choice for the specified budget.'}</td>`).join('')}
            </tr>
        `;
        $('#compareBodyRow').innerHTML = bHtml;
    }

    window.findBestProduct = async function() {
        if (state.compareIndices.length < 2) return;
        
        const btn = $('#btnFindBest');
        const verdictContainer = $('#bestProductVerdict');
        const items = state.compareIndices.map(idx => state.lastResults[idx]);
        
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>AI is Analyzing...';
        
        try {
            const resp = await fetch('/compare', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ products: items })
            });
            
            if (!resp.ok) throw new Error('AI Comparison failed');
            
            const data = await resp.json();
            const best = data.best_product;
            
            verdictContainer.innerHTML = `
                <div class="glass-card expert-verdict-card neon-glow-subtle">
                    <div class="expert-ribbon"><i class="fas fa-crown me-1"></i>Expert Pick</div>
                    <div class="row align-items-center mt-3">
                        <div class="col-md-2 text-center">
                            <i class="fas fa-microchip fa-4x text-accent mb-3"></i>
                        </div>
                        <div class="col-md-7">
                            <h4 class="fw-800 font-serif" style="color:#111827 !important;opacity:1 !important;background:rgba(255,255,255,0.98);padding:6px 12px;border-radius:12px;display:inline-block;box-decoration-break:clone;-webkit-box-decoration-break:clone;text-shadow:none;filter:none;">${best.name}</h4>
                            <p class="mb-0 text-secondary">${data.best_product_reason}</p>
                        </div>
                        <div class="col-md-3 text-end">
                            <div class="h4 fw-800 text-gold">${formatPrice(best.price_inr)}</div>
                            <a href="${best.product_link}" target="_blank" class="btn btn-premium mt-2 w-100">Claim Best Deal</a>
                        </div>
                    </div>
                </div>
            `;
            verdictContainer.style.display = 'block';
            verdictContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
            
        } catch (e) {
            showToast(e.message, 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-crown me-2"></i>Find the Best Product';
        }
    };

    // ─── MODALS & UTILITIES ──────────────────────────────────
    window.openDetail = function(index) {
        const p = state.lastResults[index];
        const content = $('#detailContent');
        if (!content) return;

        content.innerHTML = `
            <div class="row align-items-center mb-4">
                <div class="col-md-5">
                    <img src="${p.image_url || ''}" class="img-fluid rounded-4 shadow-sm border p-3" style="background:#fff">
                </div>
                <div class="col-md-7">
                    <h4 class="product-title fw-800 mb-2">${p.name}</h4>
                    <div class="h3 font-serif fw-800 text-primary mb-3">${formatPrice(p.price_inr)}</div>
                    <div class="match-score-container">
                        <div class="score-label"><span>Heuristic Match Score</span><span>${p.match_score}%</span></div>
                        <div class="progress-bar-bg"><div class="progress-bar-fill score-high" style="width: ${p.match_score}%"></div></div>
                    </div>
                </div>
            </div>
            <div class="p-4 glass-card mb-4">
                 <h6 class="fw-800 text-primary mb-3">AI Decision Analysis</h6>
                 <p class="text-secondary mb-4">${p.ai_reason || p.reason || 'This product was selected for its high feature alignment and competitive retail pricing.'}</p>
                 <div class="row">
                     <div class="col-md-6 mb-3">
                         <div class="fw-700 text-success small mb-2"><i class="fas fa-check-circle me-1"></i> WHY THIS WORKS</div>
                         <ul class="small ps-3 text-secondary">${(p.pros || []).map(pr => `<li>${pr}</li>`).join('')}</ul>
                     </div>
                     <div class="col-md-6 mb-3">
                         <div class="fw-700 text-danger small mb-2"><i class="fas fa-times-circle me-1"></i> POTENTIAL TRADE-OFFS</div>
                         <ul class="small ps-3 text-secondary">${(p.cons || []).map(co => `<li>${co}</li>`).join('')}</ul>
                     </div>
                 </div>
            </div>
            <div class="d-flex gap-3">
                 <a href="${p.product_link}" target="_blank" class="btn btn-premium flex-grow-1 py-3"><i class="fas fa-shopping-cart me-2"></i>Visit Retailer</a>
                 <button class="btn btn-outline px-4" data-bs-dismiss="modal">Close</button>
            </div>
        `;
        const modal = new bootstrap.Modal('#detailModal');
        modal.show();
    };

    window.toggleFavorite = function(index) {
        const p = state.lastResults[index];
        const alreadyFav = state.favorites.some(f => f.name === p.name);
        
        if (alreadyFav) {
            state.favorites = state.favorites.filter(f => f.name !== p.name);
            showToast('Removed from favorites', 'info');
        } else {
            state.favorites.push(p);
            showToast('Added to favorites!', 'success');
        }
        localStorage.setItem('sh_favorites', JSON.stringify(state.favorites));
        updateFavCount();
        renderProductGrid(state.lastResults);
        updateRecommendationsDisplay();
    };

    function updateFavCount() {
        const count = state.favorites.length;
        // Optionally update a badge in navbar
    }

    window.openFavoritesModal = function() {
        const container = $('#favoritesContainer');
        if (state.favorites.length === 0) {
            container.innerHTML = '<div class="text-center py-5 opacity-50"><i class="fas fa-heart fa-3x mb-3"></i><p>No favorites saved yet.</p></div>';
        } else {
            container.innerHTML = `<div class="list-group list-group-flush">
                ${state.favorites.map((f, i) => `
                    <div class="list-group-item d-flex align-items-center gap-3 py-3 border-light">
                        <img src="${f.image_url || ''}" class="rounded border p-1" style="width:50px;height:50px;object-fit:contain">
                        <div class="flex-grow-1">
                            <div class="fw-700 small text-truncate" style="max-width:300px">${f.name}</div>
                            <div class="text-primary fw-800 small">${formatPrice(f.price_inr)}</div>
                        </div>
                        <button class="btn btn-sm btn-outline-danger border-0" onclick="removeFavorite(${i})"><i class="fas fa-trash"></i></button>
                        <a href="${f.product_link}" target="_blank" class="btn btn-sm btn-light border"><i class="fas fa-external-link-alt"></i></a>
                    </div>
                `).join('')}
            </div>`;
        }
        new bootstrap.Modal('#favoritesModal').show();
    };

    window.removeFavorite = function(i) {
        state.favorites.splice(i, 1);
        localStorage.setItem('sh_favorites', JSON.stringify(state.favorites));
        openFavoritesModal();
        renderProductGrid(state.lastResults);
    };

    function formatPrice(val) {
        if (!val) return '₹ N/A';
        return '₹' + Number(val).toLocaleString('en-IN');
    }

    window.suggestSearch = function(query) {
        // Fill the search box with the suggested query
        $('#aiQuery').value = query;
        // Hide the off-topic card
        $('#offTopicCard').style.display = 'none';
        // Focus on search input
        $('#aiQuery').focus();
        // Auto-submit the search with a slight delay
        setTimeout(() => performAISearch(), 200);
    };

    function showToast(msg, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `custom-toast animate__animated animate__fadeInRight ${type}`;
        toast.innerHTML = `<i class="fas ${type === 'success' ? 'fa-check' : (type === 'error' ? 'fa-times' : 'fa-info')} me-2"></i> ${msg}`;
        $('#toastContainer').appendChild(toast);
        setTimeout(() => toast.remove(), 4000);
    }

    function escapeHtml(value) {
        return String(value || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    // Export showPage to global namespace for base.html
    window.SHG_APP = { showPage };

})();
