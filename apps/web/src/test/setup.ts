import '@testing-library/jest-dom';

// Polyfill scrollTo / scrollIntoView for jsdom
window.HTMLElement.prototype.scrollIntoView = function () {};
