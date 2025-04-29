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

// Mouse movement parallax effect for book items
document.addEventListener('DOMContentLoaded', function() {
    const bookItems = document.querySelectorAll('.book-item');
    
    bookItems.forEach(item => {
        item.addEventListener('mousemove', handleMouseMove);
        item.addEventListener('mouseleave', handleMouseLeave);
    });
    
    function handleMouseMove(e) {
        const card = this;
        const cardRect = card.getBoundingClientRect();
        
        // Calculate mouse position relative to the center of the card
        const cardCenterX = cardRect.left + cardRect.width / 2;
        const cardCenterY = cardRect.top + cardRect.height / 2;
        
        // Calculate mouse offset from center (-1 to 1)
        const mouseX = (e.clientX - cardCenterX) / (cardRect.width / 2);
        const mouseY = (e.clientY - cardCenterY) / (cardRect.height / 2);
        
        // Apply rotation based on mouse position
        const rotateY = mouseX * 10; // Rotation amount in degrees
        const rotateX = -mouseY * 10; // Inverse Y for natural tilt
        
        // Apply transforms
        card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateZ(20px)`;
        
        // Create light reflection effect
        const glareX = 100 - (mouseX + 1) * 50; // Convert -1...1 to 0...100
        const glareY = 100 - (mouseY + 1) * 50;
        
        // Apply subtle shadow based on mouse position
        card.style.boxShadow = `
            ${-mouseX * 15}px ${-mouseY * 15}px 20px rgba(0, 0, 0, 0.2),
            0 10px 20px rgba(0, 0, 0, 0.15)
        `;
        
        // Apply movement to child elements for enhanced parallax
        const cover = card.querySelector('.book-cover');
        
        
        if (cover) cover.style.transform = `translateX(${mouseX * 4}px) translateY(${mouseY * 4}px) translateZ(30px)`;
    }
    
    function handleMouseLeave(e) {
        const card = this;
        
        // Reset all transformations with smooth transition
        card.style.transform = '';
        card.style.boxShadow = '';
        
        const cover = card.querySelector('.book-cover');
        const title = card.querySelector('h3');
        const author = card.querySelector('.author');
        
        if (cover) cover.style.transform = '';
        if (title) title.style.transform = '';
        if (author) author.style.transform = '';
    }
});