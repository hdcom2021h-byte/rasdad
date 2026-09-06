(() => {
    const root = document.getElementById('community');
    if (!root || root.dataset.ready) return;
    root.dataset.ready = 'true';
    root.innerHTML = `<div class="community-heading"><span class="community-eyebrow">مجتمع رصداد</span><h2>رأيك يهمنا</h2><p>نسعد بتجربتك، ونتطور بتقييمك.</p></div>
    <div class="community-layout"><div class="community-overview"><div class="community-stats" aria-busy="true"><div><span>زوار الموقع</span><strong id="visitor-count">—</strong></div><div><span>متوسط التقييم</span><strong id="rating-average">—</strong><small id="rating-count"></small></div></div><div class="community-feedback" hidden><p id="community-state" role="status"></p><button type="button" id="community-retry">إعادة المحاولة</button></div><div class="reviews-list" aria-label="تقييمات العملاء"></div></div>
    <form id="review-form"><h3>قيّم تجربتك مع رصداد</h3><label for="review-name">الاسم<input id="review-name" name="name" required minlength="2" maxlength="80" autocomplete="name" placeholder="اكتب اسمك"></label><fieldset><legend>تقييمك</legend><div class="rating-picker">${[1,2,3,4,5].map(n => `<label class="rating-choice"><input type="radio" name="rating" value="${n}" required aria-label="${n} من 5"><span aria-hidden="true">★</span></label>`).join('')}</div><span class="rating-caption">اختر عدد النجوم</span></fieldset><button type="submit" class="review-submit">نشر التقييم <span aria-hidden="true">←</span></button><p role="status" id="review-status"></p></form></div>`;
    const form = root.querySelector('form'), feedback = root.querySelector('.community-feedback'), state = root.querySelector('#community-state'), retry = root.querySelector('#community-retry'), stats = root.querySelector('.community-stats');
    const apiBase = new URL('api/', document.baseURI);
    let visited = false, loading = false;
    async function request(path, data) {
        const controller = new AbortController(), timeout = setTimeout(() => controller.abort(), 10000);
        try {
            const response = await fetch(new URL(path, apiBase), {method: data === undefined ? 'GET' : 'POST', headers: data === undefined ? {} : {'Content-Type': 'application/json'}, body: data === undefined ? undefined : JSON.stringify(data), cache: 'no-store', credentials: 'same-origin', signal: controller.signal});
            if (!response.ok || !response.headers.get('Content-Type')?.includes('application/json')) throw new Error('Service unavailable');
            return await response.json();
        } finally { clearTimeout(timeout); }
    }
    function render(data) {
        root.querySelector('#visitor-count').textContent = data.visitors.toLocaleString('ar-SA');
        root.querySelector('#rating-average').textContent = data.count ? `${data.average.toLocaleString('ar-SA', {maximumFractionDigits: 1})} / ٥` : '—';
        root.querySelector('#rating-count').textContent = data.count ? `${data.count.toLocaleString('ar-SA')} تقييم` : 'بانتظار أول تقييم';
        const list = root.querySelector('.reviews-list'); list.replaceChildren();
        if (!data.reviews.length) {
            const empty = document.createElement('p'); empty.className = 'reviews-empty'; empty.textContent = 'كن أول من يشاركنا تقييمه.'; list.append(empty);
        }
        data.reviews.forEach(review => {
            const article = document.createElement('article'), name = document.createElement('h3'), stars = document.createElement('span');
            name.textContent = review.name;
            stars.className = 'review-stars'; stars.textContent = '★'.repeat(review.rating) + '☆'.repeat(5-review.rating); stars.setAttribute('aria-label', `${review.rating} من 5`);
            article.append(name, stars); list.append(article);
        });
    }
    async function refresh() {
        if (loading) return;
        loading = true; retry.disabled = true; stats.setAttribute('aria-busy', 'true');
        try {
            if (!visited) { try { await request('visit', {}); visited = true; } catch {} }
            render(await request('community')); feedback.hidden = true;
        } catch { state.textContent = 'الإحصاءات غير متاحة الآن.'; feedback.hidden = false; }
        finally { loading = false; retry.disabled = false; stats.setAttribute('aria-busy', 'false'); }
    }
    retry.addEventListener('click', refresh); window.addEventListener('online', refresh);
    form.addEventListener('change', () => {
        const value = Number(form.elements.rating.value);
        root.querySelectorAll('.rating-choice').forEach((choice, index) => choice.classList.toggle('selected', index < value));
        root.querySelector('.rating-caption').textContent = value ? `${value} من 5` : 'اختر عدد النجوم';
    });
    form.addEventListener('submit', async event => {
        event.preventDefault();
        const button = form.querySelector('[type=submit]'), status = root.querySelector('#review-status');
        button.disabled = true; status.textContent = 'جارٍ نشر تقييمك…';
        try {
            await request('reviews', {name: form.elements.name.value.trim(), rating: Number(form.elements.rating.value)});
            status.textContent = 'شكرًا لك، تم نشر تقييمك.'; form.reset(); form.dispatchEvent(new Event('change')); await refresh();
        } catch { status.textContent = 'لم يُنشر التقييم. يرجى إعادة المحاولة.'; }
        finally { button.disabled = false; }
    });
    refresh();
})();
