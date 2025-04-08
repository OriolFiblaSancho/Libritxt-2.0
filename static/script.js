function buscarLlibre() {
    const query = document.getElementById('search').value.toLowerCase();
    const books = document.querySelectorAll('.book-item');
    books.forEach(book => {
        const title = book.querySelector('h3').textContent.toLowerCase();
        const author = book.querySelector('.author').textContent.toLowerCase();
        if (title.includes(query) || author.includes(query)) {
            book.style.display = 'block';
        } else {
            book.style.display = 'none';
        }
    });
}