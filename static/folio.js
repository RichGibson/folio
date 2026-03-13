(function () {
  var THEME_KEY   = 'folio-theme';
  var SIDEBAR_KEY = 'folio-sidebar';

  // Apply saved theme immediately to avoid flash
  var savedTheme = localStorage.getItem(THEME_KEY) || 'light';
  document.documentElement.dataset.theme = savedTheme;

  window.toggleTheme = function () {
    var t = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = t;
    localStorage.setItem(THEME_KEY, t);
    updateThemeBtn();
  };

  function updateThemeBtn() {
    var btn = document.getElementById('theme-btn');
    if (btn) btn.textContent = document.documentElement.dataset.theme === 'dark' ? '☀' : '🌙';
  }

  window.toggleSidebar = function () {
    var layout = document.getElementById('layout');
    if (!layout) return;
    var hidden = layout.classList.toggle('sidebar-hidden');
    localStorage.setItem(SIDEBAR_KEY, hidden ? 'closed' : 'open');
  };

  window.setSort = function (key, dir) {
    applySort(key, dir, true);
  };

  function applySort(key, dir, save) {
    document.querySelectorAll('.sort-btn').forEach(function (btn) {
      btn.classList.toggle('active', btn.dataset.sort === key + '-' + dir);
    });
    document.querySelectorAll('ul.filelist').forEach(function (ul) {
      var items = Array.from(ul.querySelectorAll('li[data-name]'));
      if (!items.length) return;
      items.sort(function (a, b) {
        var cmp;
        if (key === 'name') {
          cmp = a.dataset.name.localeCompare(b.dataset.name, undefined, {sensitivity: 'base'});
        } else {
          cmp = parseFloat(a.dataset.mtime) - parseFloat(b.dataset.mtime);
        }
        return dir === 'asc' ? cmp : -cmp;
      });
      items.forEach(function (item) { ul.appendChild(item); });
    });
    if (save) localStorage.setItem('folio-sort', key + '-' + dir);
  }

  document.addEventListener('DOMContentLoaded', function () {
    updateThemeBtn();

    var layout = document.getElementById('layout');
    if (layout && localStorage.getItem(SIDEBAR_KEY) === 'closed') {
      layout.classList.add('sidebar-hidden');
    }

    // Restore sort preference on directory pages
    if (document.querySelector('.sort-btn')) {
      var saved = localStorage.getItem('folio-sort') || 'mtime-desc';
      var parts = saved.split('-');
      if (parts.length === 2) applySort(parts[0], parts[1], false);
    }
  });
}());
