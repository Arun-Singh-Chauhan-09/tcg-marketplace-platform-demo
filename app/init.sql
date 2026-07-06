CREATE TABLE IF NOT EXISTS cards (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  game ENUM('mtg','pokemon','yugioh') NOT NULL,
  rarity VARCHAR(32),
  INDEX idx_name (name)
);
CREATE TABLE IF NOT EXISTS prices (
  card_id INT PRIMARY KEY,
  avg_price_eur DECIMAL(10,2),
  min_price_eur DECIMAL(10,2),
  offers INT,
  FOREIGN KEY (card_id) REFERENCES cards(id)
);
INSERT INTO cards (name, game, rarity) VALUES
 ('Charizard Base Set', 'pokemon', 'holo rare'),
 ('Black Lotus', 'mtg', 'rare'),
 ('Blue-Eyes White Dragon', 'yugioh', 'ultra rare');
INSERT INTO prices VALUES (1, 320.50, 189.00, 412), (2, 24500.00, 18000.00, 7), (3, 45.20, 12.99, 1830);
