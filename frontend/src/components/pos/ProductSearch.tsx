import { useState, useEffect, useRef, useCallback, RefObject, KeyboardEvent } from 'react';
import { Product } from '../../types';
import { api } from '../../services/api';
import { formatRupees } from '../../utils/money';

interface ProductSearchProps {
  onSelectProduct: (product: Product) => void;
  inputRef?: RefObject<HTMLInputElement>;
}

export const ProductSearch: React.FC<ProductSearchProps> = ({
  onSelectProduct,
  inputRef: externalRef,
}) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Product[]>([]);
  const [selectedIndex, setSelectedIndex] = useState<number>(-1);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);

  const internalRef = useRef<HTMLInputElement>(null);
  const inputRef = externalRef || internalRef;
  const containerRef = useRef<HTMLDivElement>(null);

  // Debounced search
  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      setIsOpen(false);
      return;
    }

    const timer = setTimeout(async () => {
      setIsLoading(true);
      try {
        const data = await api.searchProducts(query.trim(), 10);
        setResults(data);
        setIsOpen(data.length > 0);
        setSelectedIndex(data.length > 0 ? 0 : -1);
      } catch (err) {
        console.error('Failed to search products:', err);
        setResults([]);
      } finally {
        setIsLoading(false);
      }
    }, 200);

    return () => clearTimeout(timer);
  }, [query]);

  // Handle clicking outside to close suggestions
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = useCallback(
    (product: Product) => {
      onSelectProduct(product);
      setQuery('');
      setResults([]);
      setIsOpen(false);
      setSelectedIndex(-1);
      inputRef.current?.focus();
    },
    [onSelectProduct, inputRef]
  );

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (results.length > 0) {
        setSelectedIndex((prev) => (prev + 1) % results.length);
      }
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (results.length > 0) {
        setSelectedIndex((prev) => (prev <= 0 ? results.length - 1 : prev - 1));
      }
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (selectedIndex >= 0 && selectedIndex < results.length) {
        handleSelect(results[selectedIndex]);
      } else if (results.length === 1) {
        handleSelect(results[0]);
      }
    } else if (e.key === 'Escape') {
      setIsOpen(false);
    }
  };

  return (
    <div className="pos-search-container" ref={containerRef}>
      <div className="pos-search-input-wrapper">
        <span className="search-icon">🔍</span>
        <input
          ref={inputRef}
          type="text"
          className="pos-search-input"
          placeholder="Scan barcode or search product name / brand (F2 to focus)..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          autoFocus
        />
        {isLoading && <span className="pos-search-spinner">⏳</span>}
        {query && (
          <button
            type="button"
            className="pos-search-clear"
            onClick={() => {
              setQuery('');
              setResults([]);
              inputRef.current?.focus();
            }}
          >
            ✕
          </button>
        )}
      </div>

      {isOpen && (
        <ul className="pos-search-dropdown">
          {results.map((product, index) => (
            <li
              key={product.id}
              className={`pos-search-item ${index === selectedIndex ? 'selected' : ''}`}
              onClick={() => handleSelect(product)}
              onMouseEnter={() => setSelectedIndex(index)}
            >
              <div className="pos-search-item-info">
                <span className="pos-search-item-name">{product.name}</span>
                {product.brand && <span className="pos-search-item-brand">{product.brand}</span>}
                {product.barcode && (
                  <span className="pos-search-item-barcode">🏷️ {product.barcode}</span>
                )}
              </div>
              <div className="pos-search-item-pricing">
                <span className="pos-search-item-price">
                  {formatRupees(product.selling_price_paise)}
                </span>
                <span className="pos-search-item-gst">GST {product.gst_rate}%</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};
