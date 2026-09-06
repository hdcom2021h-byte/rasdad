(() => {
    const root = document.getElementById('community');
    if (!root || root.dataset.ready) return;
    root.dataset.ready = 'true';
    root.innerHTML = '<div class="community-heading"><span class="community-eyebrow">رصداد</span><h2>رأيك يهمنا</h2><p>شاركنا تقييم تجربتك عبر واتساب.</p></div><form id="review-form"><h3>قيّم تجربتك مع رصداد</h3><label for="review-name">الاسم<input id="review-name" name="name" required minlength="2" maxlength="80" autocomplete="name" placeholder="اكتب اسمك"></label><fieldset><legend>تقييمك</legend><div class="rating-picker"></div><span class="rating-caption">اختر عدد النجوم</span></fieldset><button type="submit" class="review-submit">إرسال التقييم عبر واتساب ←</button><p role="status" id="review-status"></p></form>';
    const form = root.querySelector('form');
    for (let n = 1; n <= 5; n++) {
        const label = document.createElement('label'); label.className = 'rating-choice';
        const input = document.createElement('input'); input.type = 'radio'; input.name = 'rating'; input.value = n; input.required = true; input.setAttribute('aria-label', n + ' من 5');
        const star = document.createElement('span'); star.textContent = '★'; star.setAttribute('aria-hidden', 'true'); label.append(input, star); root.querySelector('.rating-picker').append(label);
    }
    form.addEventListener('change', () => {
        const value = Number(form.elements.rating.value);
        root.querySelectorAll('.rating-choice').forEach((choice, index) => choice.classList.toggle('selected', index < value));
        root.querySelector('.rating-caption').textContent = value ? value + ' من 5' : 'اختر عدد النجوم';
    });
    form.addEventListener('submit', event => {
        event.preventDefault();
        const name = form.elements.name.value.trim(), rating = Number(form.elements.rating.value);
        if (name.length < 2) { form.elements.name.setCustomValidity('يرجى كتابة اسم صحيح.'); form.elements.name.reportValidity(); return; }
        const message = 'تقييم تجربة رصداد\nالاسم: ' + name + '\nالتقييم: ' + rating + ' من 5 ' + '★'.repeat(rating);
        window.open('https://wa.me/966563962821?text=' + encodeURIComponent(message), '_blank', 'noopener,noreferrer');
        root.querySelector('#review-status').textContent = 'أكمل إرسال تقييمك في واتساب.';
    });
    form.elements.name.addEventListener('input', () => form.elements.name.setCustomValidity(''));
})();
