    const pageKind = document.body.dataset.page || 'index';
    const favoriteStorageKey = 'productReferenceFavorites';
    const deletedStorageKey = 'productReferenceDeleted';
    const cloudHiddenEndpoint = '/api/hidden';
    const cloudDeleteEndpoint = '/api/delete';
    const search = document.getElementById('search');
    const reset = document.getElementById('reset');
    const exportDeletes = document.getElementById('export-deletes');
    const clearDeletes = document.getElementById('clear-deletes');
    let cards = Array.from(document.querySelectorAll('article[data-text]'));
    const visibleCount = document.getElementById('visible-count');
    const favoriteCount = document.getElementById('favorite-count');
    const empty = document.getElementById('empty');
    let activeCategory = '';
    let pendingDeleteButton = null;
    let pendingDeleteTimer = 0;
    let favoriteTotal = favoriteCount ? Number(favoriteCount.dataset.count || favoriteCount.textContent || '0') : 0;

    function readStoredList(key) {
      try {
        return new Set(JSON.parse(localStorage.getItem(key) || '[]'));
      } catch (error) {
        return new Set();
      }
    }

    function writeStoredList(key, ids) {
      try {
        localStorage.setItem(key, JSON.stringify(Array.from(ids).sort()));
      } catch (error) {
        // Ignore storage errors so the controls still work for the current page view.
      }
    }

    function readStoredFavorites() {
      return readStoredList(favoriteStorageKey);
    }

    function writeStoredFavorites(ids) {
      writeStoredList(favoriteStorageKey, ids);
    }

    function readStoredDeleted() {
      return readStoredList(deletedStorageKey);
    }

    function writeStoredDeleted(ids) {
      writeStoredList(deletedStorageKey, ids);
    }

    let storedFavorites = readStoredFavorites();
    let storedDeleted = readStoredDeleted();
    let cloudDeleted = new Set();

    function deleteSyncFilename() {
      const stamp = new Date().toISOString().replace(/[:.]/g, '-');
      return `gallery-delete-sync-${stamp}.json`;
    }

    function updateDeleteSyncControls() {
      const count = storedDeleted.size;
      if (exportDeletes) {
        exportDeletes.disabled = count === 0;
        exportDeletes.textContent = count ? `导出删除清单(${count})` : '导出删除清单';
        exportDeletes.title = count ? '下载当前浏览器的删除清单，用于同步到本地项目' : '当前浏览器没有删除记录';
      }
      if (clearDeletes) {
        clearDeletes.disabled = count === 0;
        clearDeletes.title = count ? '清空当前浏览器的删除记录并刷新页面' : '当前浏览器没有删除记录';
      }
    }

    function exportDeletedList() {
      const ids = Array.from(storedDeleted).sort();
      if (!ids.length) return;
      const payload = {
        version: 1,
        generatedAt: new Date().toISOString(),
        source: window.location.href,
        storageKey: deletedStorageKey,
        ids
      };
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = deleteSyncFilename();
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    }

    function clearStoredDeletes() {
      if (!storedDeleted.size) return;
      if (!window.confirm('要恢复这个浏览器里隐藏的卡片吗？这只会清空网页端删除记录，不会改本地项目。')) return;
      storedDeleted = new Set();
      writeStoredDeleted(storedDeleted);
      window.location.reload();
    }

    function combinedDeletedIds() {
      const ids = new Set(storedDeleted);
      for (const id of cloudDeleted) ids.add(id);
      return ids;
    }

    function cardDeletePayload(card) {
      const productLink = card.querySelector('.links a[href], .thumb[href]');
      const imageLink = card.querySelectorAll('.links a[href]')[1];
      const image = card.querySelector('.thumb img');
      return {
        id: card.dataset.id,
        title: card.dataset.title || '',
        source: card.dataset.source || '',
        category: card.dataset.category || '',
        product_url: productLink ? productLink.href : '',
        image_url: imageLink ? imageLink.href : '',
        thumb_url: image ? image.getAttribute('src') : '',
        page_url: window.location.href
      };
    }

    function applyFilters() {
      const q = search.value.trim().toLowerCase();
      let shown = 0;
      for (const card of cards) {
        const text = card.dataset.text || '';
        const category = card.dataset.category || '';
        const okSearch = !q || text.includes(q);
        const okCategory = !activeCategory || category === activeCategory;
        const okFavorite = pageKind !== 'favorites' || card.dataset.favorite === '1';
        const show = okSearch && okCategory && okFavorite;
        card.style.display = show ? '' : 'none';
        if (show) shown++;
      }
      visibleCount.textContent = shown;
      empty.style.display = shown ? 'none' : 'block';
    }

    document.querySelectorAll('.chip').forEach((button) => {
      button.addEventListener('click', () => {
        activeCategory = activeCategory === button.dataset.filter ? '' : button.dataset.filter;
        document.querySelectorAll('.chip').forEach((b) => b.classList.toggle('active', b === button && activeCategory));
        applyFilters();
      });
    });

    search.addEventListener('input', applyFilters);
    reset.addEventListener('click', () => {
      search.value = '';
      activeCategory = '';
      document.querySelectorAll('.chip.active').forEach((b) => b.classList.remove('active'));
      applyFilters();
    });

    function setFavoriteButton(button, isFavorite) {
      button.classList.toggle('is-favorite', isFavorite);
      button.textContent = isFavorite ? '★' : '☆';
      const label = isFavorite ? '取消收藏' : '收藏';
      button.title = label;
      button.setAttribute('aria-label', label);
      const card = button.closest('article');
      if (card) card.dataset.favorite = isFavorite ? '1' : '0';
    }

    function setFavoriteCount(value) {
      favoriteTotal = Math.max(0, Number(value) || 0);
      if (!favoriteCount) return;
      favoriteCount.textContent = favoriteTotal;
      favoriteCount.dataset.count = String(favoriteTotal);
    }

    function updateStoredFavorite(id, isFavorite) {
      if (isFavorite) storedFavorites.add(id);
      else storedFavorites.delete(id);
      writeStoredFavorites(storedFavorites);
      setFavoriteCount(storedFavorites.size);
    }

    function applyStoredFavorites() {
      for (const button of document.querySelectorAll('.favorite-card')) {
        const card = button.closest('article');
        if (!card) continue;
        const id = card.dataset.id;
        if (button.classList.contains('is-favorite')) storedFavorites.add(id);
        if (storedFavorites.has(id)) setFavoriteButton(button, true);
      }
      writeStoredFavorites(storedFavorites);
      if (storedFavorites.size) setFavoriteCount(storedFavorites.size);
    }

    function applyStoredDeletes() {
      let changedFavorites = false;
      const hiddenIds = combinedDeletedIds();
      for (const card of Array.from(document.querySelectorAll('article[data-id]'))) {
        const id = card.dataset.id;
        if (!hiddenIds.has(id)) continue;
        if (storedFavorites.delete(id)) changedFavorites = true;
        card.remove();
      }
      cards = Array.from(document.querySelectorAll('article[data-text]'));
      if (changedFavorites) {
        writeStoredFavorites(storedFavorites);
        setFavoriteCount(storedFavorites.size);
      }
      updateDeleteSyncControls();
    }

    async function loadCloudDeleted() {
      try {
        const response = await fetch(cloudHiddenEndpoint, { cache: 'no-store' });
        const result = await response.json();
        if (!response.ok || !result.ok) throw new Error(result.message || result.error || 'hidden list unavailable');
        cloudDeleted = new Set((result.ids || []).map(String));
        applyStoredDeletes();
        applyFilters();
      } catch (error) {
        console.warn('Cloud delete list unavailable; using local fallback only.', error);
      }
    }

    async function toggleFavorite(button) {
      const card = button.closest('article');
      if (!card) return;
      const id = card.dataset.id;
      const nextFavorite = !button.classList.contains('is-favorite');
      button.disabled = true;
      try {
        const response = await fetch('/api/favorite', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id, favorite: nextFavorite })
        });
        if (!response.ok) throw new Error(await response.text());
        const result = await response.json();
        setFavoriteButton(button, Boolean(result.favorite));
        setFavoriteCount(result.favorite_count);
        updateStoredFavorite(id, Boolean(result.favorite));
        if (pageKind === 'favorites' && !result.favorite) {
          applyFilters();
        }
      } catch (error) {
        setFavoriteButton(button, nextFavorite);
        updateStoredFavorite(id, nextFavorite);
        if (pageKind === 'favorites' && !nextFavorite) applyFilters();
      } finally {
        button.disabled = false;
      }
    }

    document.querySelectorAll('.favorite-card').forEach((button) => {
      button.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        toggleFavorite(button);
      });
    });

    function resetDeleteButton(button) {
      if (!button) return;
      button.dataset.confirm = '';
      button.classList.remove('confirming');
      button.textContent = '×';
      button.title = '删除这张参考图';
      button.setAttribute('aria-label', '删除这张参考图');
      if (pendingDeleteButton === button) pendingDeleteButton = null;
    }

    function resetPendingDelete(exceptButton = null) {
      if (pendingDeleteTimer) {
        clearTimeout(pendingDeleteTimer);
        pendingDeleteTimer = 0;
      }
      if (pendingDeleteButton && pendingDeleteButton !== exceptButton) {
        resetDeleteButton(pendingDeleteButton);
      }
    }

    async function deleteCard(button) {
      const card = button.closest('article');
      if (!card) return;
      resetPendingDelete(button);
      const id = card.dataset.id;
      button.disabled = true;
      button.textContent = '删除中';
      card.classList.add('is-deleting');
      try {
        const response = await fetch(cloudDeleteEndpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(cardDeletePayload(card))
        });
        if (!response.ok) throw new Error(await response.text());
        cloudDeleted.add(id);
        card.remove();
        cards = Array.from(document.querySelectorAll('article[data-text]'));
        resetPendingDelete();
        if (storedFavorites.delete(id)) {
          writeStoredFavorites(storedFavorites);
          setFavoriteCount(storedFavorites.size);
        }
        applyFilters();
      } catch (error) {
        storedDeleted.add(id);
        writeStoredDeleted(storedDeleted);
        if (storedFavorites.delete(id)) {
          writeStoredFavorites(storedFavorites);
          setFavoriteCount(storedFavorites.size);
        }
        card.remove();
        cards = Array.from(document.querySelectorAll('article[data-text]'));
        resetPendingDelete();
        updateDeleteSyncControls();
        applyFilters();
      }
    }

    document.querySelectorAll('.delete-card').forEach((button) => {
      button.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        if (button.dataset.confirm === '1') {
          deleteCard(button);
          return;
        }
        resetPendingDelete(button);
        pendingDeleteButton = button;
        button.dataset.confirm = '1';
        button.classList.add('confirming');
        button.textContent = '确认删除';
        button.title = '再次点击确认删除';
        button.setAttribute('aria-label', '再次点击确认删除');
        pendingDeleteTimer = setTimeout(() => resetDeleteButton(button), 4000);
      });
    });

    document.addEventListener('click', (event) => {
      if (!event.target.closest('.delete-card')) resetPendingDelete();
    });

    if (exportDeletes) exportDeletes.addEventListener('click', exportDeletedList);
    if (clearDeletes) clearDeletes.addEventListener('click', clearStoredDeletes);

    applyStoredFavorites();
    applyStoredDeletes();
    updateDeleteSyncControls();
    applyFilters();
    loadCloudDeleted();
