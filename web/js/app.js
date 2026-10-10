/**
 * KPSS Atama & Personel Alım Takip Sistemi - Frontend İstemci Denetleyicisi
 * UI - Backend mutlak ayrımına uygun olarak strictly REST API üzerinden haberleşir.
 */

// Uygulama Durumu (State)
const state = {
    searchText: '',
    selectedPortal: '',
    scoreFilter: '', // '', 'P3', 'CAREER'
    limit: 20,
    offset: 0,
    total: 0,
    isScraping: false,
    theme: localStorage.getItem('kpss_theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
};

// DOM Elemanları
const el = {
    // Tema
    btnThemeToggle: document.getElementById('btnThemeToggle'),
    themeIcon: document.getElementById('themeIcon'),

    // İstatistikler
    statP3Count: document.getElementById('statP3Count'),
    statCareerCount: document.getElementById('statCareerCount'),
    statTotalCount: document.getElementById('statTotalCount'),
    statUnnotifiedCount: document.getElementById('statUnnotifiedCount'),
    statCardP3: document.getElementById('statCardP3'),
    statCardCareer: document.getElementById('statCardCareer'),
    statCardTotal: document.getElementById('statCardTotal'),

    // Filtreler
    searchInput: document.getElementById('searchInput'),
    portalFilter: document.getElementById('portalFilter'),
    scoreFilterGroup: document.getElementById('scoreFilterGroup'),
    resultCountText: document.getElementById('resultCountText'),

    // İlan Konteyneri ve Sayfalama
    announcementsContainer: document.getElementById('announcementsContainer'),
    paginationContainer: document.getElementById('paginationContainer'),
    btnPrevPage: document.getElementById('btnPrevPage'),
    btnNextPage: document.getElementById('btnNextPage'),
    pageInfoText: document.getElementById('pageInfoText'),

    // Portal Durum Paneli
    portalStatusGrid: document.getElementById('portalStatusGrid'),

    // Aksiyon Butonları
    btnTriggerScrape: document.getElementById('btnTriggerScrape'),
    scrapeBtnIcon: document.getElementById('scrapeBtnIcon'),
    scrapeBtnText: document.getElementById('scrapeBtnText'),

    // Ayarlar & Telegram Modalı
    settingsModal: document.getElementById('settingsModal'),
    btnSettingsModal: document.getElementById('btnSettingsModal'),
    btnCloseSettingsModal: document.getElementById('btnCloseSettingsModal'),
    btnDismissModal: document.getElementById('btnDismissModal'),
    tgStatusBadge: document.getElementById('tgStatusBadge'),
    inputChatId: document.getElementById('inputChatId'),
    btnTestTelegram: document.getElementById('btnTestTelegram'),
    telegramTestFeedback: document.getElementById('telegramTestFeedback'),

    // Toast
    toastContainer: document.getElementById('toastContainer')
};

// 0. Tema Yönetimi (Dark / Light Mode)
function applyTheme(theme) {
    state.theme = theme;
    localStorage.setItem('kpss_theme', theme);
    if (theme === 'dark') {
        document.documentElement.classList.add('dark');
        el.themeIcon.textContent = '☀️';
        el.btnThemeToggle.title = 'Aydınlık Moda Geç';
    } else {
        document.documentElement.classList.remove('dark');
        el.themeIcon.textContent = '🌙';
        el.btnThemeToggle.title = 'Karanlık Moda Geç';
    }
}

function toggleTheme() {
    const nextTheme = state.theme === 'dark' ? 'light' : 'dark';
    applyTheme(nextTheme);
    showToast(`Tema değiştirildi: ${nextTheme === 'dark' ? 'Karanlık Mod 🌙' : 'Aydınlık Mod ☀️'}`, 'info');
}

// Yardımcı: Toast Bildirimi Göster
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    const bgClass = type === 'success' 
        ? 'bg-emerald-600 text-white' 
        : (type === 'error' ? 'bg-rose-600 text-white' : 'bg-slate-900 dark:bg-slate-800 text-white border border-slate-700');
    toast.className = `toast pointer-events-auto flex items-center space-x-2 px-4 py-3 rounded-xl shadow-lg text-xs font-semibold ${bgClass}`;
    toast.innerHTML = `<span>${type === 'success' ? '✅' : (type === 'error' ? '❌' : 'ℹ️')}</span><span>${message}</span>`;
    
    el.toastContainer.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// 1. İstatistikleri Çek
async function fetchStats() {
    try {
        const res = await fetch('/api/announcements/stats');
        if (!res.ok) return;
        const stats = await res.json();

        el.statP3Count.textContent = stats.p3_count || 0;
        el.statCareerCount.textContent = stats.p1_p2_count || 0;
        el.statTotalCount.textContent = stats.total_announcements || 0;
        el.statUnnotifiedCount.textContent = stats.total_unnotified || 0;
    } catch (err) {
        console.error('İstatistikler yüklenemedi:', err);
    }
}

// 2. İlanları Listele
async function fetchAnnouncements() {
    el.announcementsContainer.innerHTML = `
        <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-8 text-center text-slate-400 dark:text-slate-500">
            <div class="inline-block animate-spin text-2xl mb-2">⏳</div>
            <p class="text-xs font-medium">İlanlar yükleniyor...</p>
        </div>
    `;

    try {
        const query = new URLSearchParams({
            limit: state.limit,
            offset: state.offset
        });

        if (state.searchText) query.append('search', state.searchText);
        if (state.selectedPortal) query.append('source_key', state.selectedPortal);

        if (state.scoreFilter === 'P3') {
            query.append('only_p3', 'true');
        } else if (state.scoreFilter === 'CAREER') {
            query.append('score_type', 'P1');
            query.append('score_type', 'P2');
        }

        const res = await fetch(`/api/announcements?${query.toString()}`);
        if (!res.ok) throw new Error('Sunucu yanıt vermedi');
        const data = await res.json();

        state.total = data.total;
        renderAnnouncements(data.items);
        updatePagination(data.total);
    } catch (err) {
        el.announcementsContainer.innerHTML = `
            <div class="bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 rounded-2xl p-6 text-center text-rose-700 dark:text-rose-300 text-xs">
                ❌ İlanlar getirilirken bir hata oluştu: ${err.message}
            </div>
        `;
    }
}

// İlan Kartlarını Ekrana Bas
function renderAnnouncements(items) {
    el.resultCountText.textContent = `Toplam ${state.total} ilan (${state.offset + 1} - ${Math.min(state.offset + items.length, state.total)} arası)`;

    if (items.length === 0) {
        el.announcementsContainer.innerHTML = `
            <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-12 text-center text-slate-500 dark:text-slate-400 space-y-3">
                <div class="text-4xl">🔍</div>
                <h4 class="font-bold text-slate-800 dark:text-slate-200 text-sm">Eşleşen İlan Bulunamadı</h4>
                <p class="text-xs text-slate-400 dark:text-slate-500">Arama kriterlerinizi değiştirerek veya "Şimdi Tara" butonuna basarak yeniden deneyin.</p>
            </div>
        `;
        return;
    }

    const html = items.map(item => {
        // Öncelik şeridi sınıfı
        let stripeClass = 'priority-normal-stripe';
        if (item.priority_level === 3) stripeClass = 'priority-p3-stripe';
        else if (item.priority_level === 2) stripeClass = 'priority-career-stripe';

        // Puan Rozetleri
        const scoreBadges = (item.matched_score_types || []).map(score => {
            if (score === 'P3') {
                return `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-indigo-100 dark:bg-indigo-950/60 text-indigo-800 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">🎓 KPSS P3 Lisans</span>`;
            } else if (score === 'P1' || score === 'P2') {
                return `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800">🎯 KPSS ${score} Kariyer</span>`;
            } else {
                return `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700">Genel Kadro</span>`;
            }
        }).join(' ');

        // Tarih Bilgisi
        const deadlineBadge = item.deadline_date ? `
            <div class="flex items-center text-xs font-semibold text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 px-2.5 py-1 rounded-lg">
                <span class="mr-1.5">📅</span>
                <span>Son Başvuru: ${item.deadline_date}</span>
            </div>
        ` : '';

        // Şehir Bilgisi
        const cityBadge = item.city ? `
            <span class="inline-flex items-center text-xs text-slate-500 dark:text-slate-400 font-medium">
                <span class="mr-1">📍</span> ${item.city}
            </span>
        ` : '';

        // PDF Linki
        const pdfButton = (item.pdf_url && item.pdf_url !== item.url) ? `
            <a href="${item.pdf_url}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center px-3 py-1.5 text-xs font-semibold text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors">
                <span class="mr-1">📄</span> PDF İlan
            </a>
        ` : '';

        return `
            <article class="announcement-card bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 sm:p-5 shadow-sm ${stripeClass}">
                <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div class="space-y-2 flex-1">
                        <!-- Portal & Rozetler -->
                        <div class="flex flex-wrap items-center gap-2">
                            <span class="inline-flex items-center text-xs font-semibold text-slate-500 dark:text-slate-400">
                                <span class="mr-1 text-sm">${item.source_icon}</span> ${item.source_name}
                            </span>
                            ${scoreBadges}
                            ${cityBadge}
                        </div>

                        <!-- Kurum & Başlık -->
                        <div>
                            <h3 class="text-xs font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 mb-0.5">
                                ${item.institution}
                            </h3>
                            <h2 class="text-sm sm:text-base font-bold text-slate-900 dark:text-white leading-snug">
                                ${item.title}
                            </h2>
                        </div>
                    </div>

                    <!-- Sağ Taraf: Tarih ve Butonlar -->
                    <div class="flex flex-row md:flex-col items-center md:items-end justify-between md:justify-center gap-2 pt-2 md:pt-0 border-t md:border-t-0 border-slate-100 dark:border-slate-800">
                        ${deadlineBadge}
                        <div class="flex items-center space-x-2">
                            ${pdfButton}
                            <a href="${item.url}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center px-3.5 py-1.5 text-xs font-bold text-white bg-brand-600 hover:bg-brand-700 rounded-lg shadow-sm transition-all active:scale-95">
                                <span>İlana Git</span>
                                <span class="ml-1 text-xs">&rarr;</span>
                            </a>
                        </div>
                    </div>
                </div>
            </article>
        `;
    }).join('');

    el.announcementsContainer.innerHTML = html;
}

// Sayfalama Kontrolleri
function updatePagination(total) {
    if (total <= state.limit) {
        el.paginationContainer.classList.add('hidden');
        return;
    }
    el.paginationContainer.classList.remove('hidden');

    const currentPage = Math.floor(state.offset / state.limit) + 1;
    const totalPages = Math.ceil(total / state.limit);

    el.pageInfoText.textContent = `Sayfa ${currentPage} / ${totalPages}`;
    el.btnPrevPage.disabled = state.offset === 0;
    el.btnNextPage.disabled = state.offset + state.limit >= total;
}

// 3. Portalların Durum Paneli
async function fetchScraperStatuses() {
    try {
        const res = await fetch('/api/scrapers/status');
        if (!res.ok) return;
        const statuses = await res.json();

        el.portalStatusGrid.innerHTML = statuses.map(s => {
            const isSuccess = s.status === 'success';
            const isError = s.status === 'error';
            const statusDot = isSuccess ? 'bg-emerald-500' : (isError ? 'bg-rose-500' : 'bg-slate-300 dark:bg-slate-600');
            const statusText = isSuccess ? `${s.found_count} İlan` : (isError ? 'Hata' : 'Beklemede');

            return `
                <div class="p-3 bg-slate-50 dark:bg-slate-800/60 border border-slate-200/80 dark:border-slate-800 rounded-xl text-center space-y-1 transition-colors">
                    <div class="text-xl mb-1">${s.portal_icon || '🌐'}</div>
                    <div class="text-xs font-bold text-slate-800 dark:text-slate-200 truncate" title="${s.portal_name}">${s.portal_name}</div>
                    <div class="inline-flex items-center text-[10px] font-semibold text-slate-600 dark:text-slate-400">
                        <span class="w-1.5 h-1.5 rounded-full ${statusDot} mr-1.5"></span>
                        ${statusText}
                    </div>
                    ${s.duration_ms > 0 ? `<div class="text-[10px] text-slate-400 dark:text-slate-500 font-mono">${Math.round(s.duration_ms)} ms</div>` : ''}
                </div>
            `;
        }).join('');
    } catch (err) {
        console.error('Portal durumları alınamadı:', err);
    }
}

// 4. Şimdi Tara Tetikleme
async function triggerScrape() {
    if (state.isScraping) return;
    state.isScraping = true;

    el.btnTriggerScrape.disabled = true;
    el.scrapeBtnIcon.classList.add('animate-spin-custom');
    el.scrapeBtnText.textContent = 'Taranıyor...';

    showToast('Tüm kamu portalları taranıyor...', 'info');

    try {
        const res = await fetch('/api/scrapers/run', { method: 'POST' });
        const data = await res.json();

        if (data.success) {
            showToast(`Tarama tamamlandı! ${data.new_announcements} yeni ilan eklendi.`, 'success');
            await fetchStats();
            await fetchScraperStatuses();
            await fetchAnnouncements();
        } else {
            showToast('Tarama sırasında bir sorun oluştu.', 'error');
        }
    } catch (err) {
        showToast(`Tarama başarısız: ${err.message}`, 'error');
    } finally {
        state.isScraping = false;
        el.btnTriggerScrape.disabled = false;
        el.scrapeBtnIcon.classList.remove('animate-spin-custom');
        el.scrapeBtnText.textContent = 'Şimdi Tara';
    }
}

// 5. Telegram Ayarları ve Testi
async function loadSettings() {
    try {
        const res = await fetch('/api/settings');
        if (!res.ok) return;
        const data = await res.json();

        el.inputChatId.value = data.telegram_chat_id || 'Tanımlanmamış';
        
        if (data.telegram_configured) {
            el.tgStatusBadge.className = 'flex items-center text-xs font-semibold px-3 py-2 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800';
            el.tgStatusBadge.innerHTML = '<span>✅ Bot Token ve Chat ID Tanımlı</span>';
        } else {
            el.tgStatusBadge.className = 'flex items-center text-xs font-semibold px-3 py-2 rounded-lg bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800';
            el.tgStatusBadge.innerHTML = '<span>⚠️ Yapılandırılmadı (.env dosyasını doldurun)</span>';
        }
    } catch (err) {
        console.error('Ayarlar yüklenemedi:', err);
    }
}

async function testTelegram() {
    el.btnTestTelegram.disabled = true;
    el.telegramTestFeedback.className = 'text-xs text-center mt-2 text-slate-500';
    el.telegramTestFeedback.textContent = 'Test mesajı iletiliyor...';
    el.telegramTestFeedback.classList.remove('hidden');

    try {
        const res = await fetch('/api/settings/telegram/test', { method: 'POST' });
        const data = await res.json();

        if (data.success) {
            el.telegramTestFeedback.className = 'text-xs text-center mt-2 text-emerald-600 dark:text-emerald-400 font-semibold';
            el.telegramTestFeedback.textContent = '✅ ' + data.message;
            showToast('Telegram bildirimi telefonunuza gönderildi!', 'success');
        } else {
            el.telegramTestFeedback.className = 'text-xs text-center mt-2 text-rose-600 dark:text-rose-400 font-semibold';
            el.telegramTestFeedback.textContent = '❌ ' + data.message;
            showToast(data.message, 'error');
        }
    } catch (err) {
        el.telegramTestFeedback.className = 'text-xs text-center mt-2 text-rose-600 dark:text-rose-400 font-semibold';
        el.telegramTestFeedback.textContent = 'Hata: ' + err.message;
    } finally {
        el.btnTestTelegram.disabled = false;
    }
}

// Olay Dinleyicileri (Event Listeners)
function setupEventListeners() {
    // Tema Değiştirici
    el.btnThemeToggle.addEventListener('click', toggleTheme);

    // Canlı Arama Debounce
    let searchTimeout;
    el.searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            state.searchText = e.target.value.trim();
            state.offset = 0;
            fetchAnnouncements();
        }, 300);
    });

    // Portal Filtresi
    el.portalFilter.addEventListener('change', (e) => {
        state.selectedPortal = e.target.value;
        state.offset = 0;
        fetchAnnouncements();
    });

    // Hızlı Puan Butonları
    el.scoreFilterGroup.querySelectorAll('.score-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            el.scoreFilterGroup.querySelectorAll('.score-btn').forEach(b => {
                b.classList.remove('bg-slate-900', 'dark:bg-white', 'text-white', 'dark:text-slate-900');
                b.classList.add('text-slate-700', 'dark:text-slate-300');
            });
            btn.classList.add('bg-slate-900', 'dark:bg-white', 'text-white', 'dark:text-slate-900');
            btn.classList.remove('text-slate-700', 'dark:text-slate-300');

            state.scoreFilter = btn.dataset.score;
            state.offset = 0;
            fetchAnnouncements();
        });
    });

    // İstatistik Kartlarına Tıklayarak Filtreleme
    el.statCardP3.addEventListener('click', () => {
        const p3Btn = el.scoreFilterGroup.querySelector('[data-score="P3"]');
        if (p3Btn) p3Btn.click();
    });

    el.statCardCareer.addEventListener('click', () => {
        const careerBtn = el.scoreFilterGroup.querySelector('[data-score="CAREER"]');
        if (careerBtn) careerBtn.click();
    });

    el.statCardTotal.addEventListener('click', () => {
        const allBtn = el.scoreFilterGroup.querySelector('[data-score=""]');
        if (allBtn) allBtn.click();
    });

    // Sayfalama Butonları
    el.btnPrevPage.addEventListener('click', () => {
        if (state.offset > 0) {
            state.offset -= state.limit;
            fetchAnnouncements();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    });

    el.btnNextPage.addEventListener('click', () => {
        if (state.offset + state.limit < state.total) {
            state.offset += state.limit;
            fetchAnnouncements();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    });

    // Şimdi Tara
    el.btnTriggerScrape.addEventListener('click', triggerScrape);

    // Modal Aç / Kapa
    el.btnSettingsModal.addEventListener('click', () => {
        loadSettings();
        el.settingsModal.classList.remove('hidden');
    });

    const closeModal = () => el.settingsModal.classList.add('hidden');
    el.btnCloseSettingsModal.addEventListener('click', closeModal);
    el.btnDismissModal.addEventListener('click', closeModal);
    el.settingsModal.addEventListener('click', (e) => {
        if (e.target === el.settingsModal) closeModal();
    });

    // Telegram Test
    el.btnTestTelegram.addEventListener('click', testTelegram);
}

// Uygulamayı Başlat
document.addEventListener('DOMContentLoaded', () => {
    applyTheme(state.theme);
    setupEventListeners();
    fetchStats();
    fetchScraperStatuses();
    fetchAnnouncements();
});
