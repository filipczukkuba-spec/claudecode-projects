export interface Item {
  id: string;
  name: string;
}

export interface StorePrice {
  item: string;
  price: number | null;
}

export interface StoreResult {
  name: string;
  logo: string;
  color: string;
  prices: StorePrice[];
  total: number;
  available: number;
}
