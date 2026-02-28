import { useEffect, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../contexts/AuthContext";
import type { Transaction, Wallet } from "../types";

const TX_LABELS: Record<string, string> = {
  deposit: "Deposit",
  purchase: "Purchase",
  escrow_release: "Sale proceeds",
  escrow_refund: "Refund received",
  payout: "Payout",
  refund_credit: "Refund credit",
  admin_adjustment: "Balance adjustment",
};

export function WalletDashboard() {
  const { user } = useAuth();
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [txTotal, setTxTotal] = useState(0);
  const [txPage, setTxPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [depositAmount, setDepositAmount] = useState("");
  const [depositLoading, setDepositLoading] = useState(false);
  const [depositSuccess, setDepositSuccess] = useState("");
  const [depositError, setDepositError] = useState("");

  const fetchData = async () => {
    const [w, txData] = await Promise.all([
      api.get<Wallet>("/wallet"),
      api.get<{ items: Transaction[]; total: number }>(`/wallet/transactions?page=${txPage}&per_page=15`),
    ]);
    setWallet(w);
    setTransactions(txData.items);
    setTxTotal(txData.total);
  };

  useEffect(() => {
    setLoading(true);
    fetchData().finally(() => setLoading(false));
  }, [txPage]);

  const handleDeposit = async (e: React.FormEvent) => {
    e.preventDefault();
    const amount = parseFloat(depositAmount);
    if (isNaN(amount) || amount <= 0) return;

    setDepositLoading(true);
    setDepositError("");
    setDepositSuccess("");

    try {
      await api.post<Wallet>("/wallet/deposit", { amount, payment_method: "card" });
      setDepositSuccess(`$${amount.toFixed(2)} added to your wallet!`);
      setDepositAmount("");
      fetchData();
    } catch (err) {
      setDepositError(err instanceof Error ? err.message : "Deposit failed");
    } finally {
      setDepositLoading(false);
    }
  };

  return (
    <div className="page">
      <h1 className="page-title">Wallet</h1>

      {loading ? (
        <div className="loading-state">Loading wallet…</div>
      ) : (
        <>
          <div className="wallet-cards">
            <div className="wallet-card wallet-card-primary">
              <span className="wallet-card-label">Available Balance</span>
              <span className="wallet-card-amount">${wallet?.balance.toFixed(2) ?? "0.00"}</span>
              <span className="wallet-card-sub">Ready to spend</span>
            </div>

            {(user?.role === "seller" || user?.role === "admin") && (
              <div className="wallet-card wallet-card-pending">
                <span className="wallet-card-label">Pending Earnings</span>
                <span className="wallet-card-amount">${wallet?.pending_balance.toFixed(2) ?? "0.00"}</span>
                <span className="wallet-card-sub">Awaiting payout</span>
              </div>
            )}

            <div className="wallet-card wallet-card-add">
              <span className="wallet-card-label">Add Funds</span>
              <form onSubmit={handleDeposit} className="deposit-form">
                <div className="deposit-input-wrap">
                  <span className="deposit-currency">$</span>
                  <input
                    type="number"
                    className="deposit-input"
                    value={depositAmount}
                    onChange={(e) => setDepositAmount(e.target.value)}
                    placeholder="0.00"
                    min="1"
                    max="10000"
                    step="0.01"
                    required
                  />
                </div>
                {depositSuccess && <p className="text-success text-sm">{depositSuccess}</p>}
                {depositError && <p className="text-danger text-sm">{depositError}</p>}
                <div className="deposit-quick">
                  {[25, 50, 100, 250].map((amt) => (
                    <button
                      key={amt}
                      type="button"
                      className="btn btn-sm btn-secondary"
                      onClick={() => setDepositAmount(String(amt))}
                    >
                      ${amt}
                    </button>
                  ))}
                </div>
                <button type="submit" className="btn btn-primary btn-full" disabled={depositLoading}>
                  {depositLoading ? "Processing…" : "Add Funds"}
                </button>
              </form>
            </div>
          </div>

          <div className="section-card">
            <h2 className="section-card-title">Transaction History</h2>

            {transactions.length === 0 ? (
              <p className="empty-message">No transactions yet.</p>
            ) : (
              <div className="transaction-list">
                {transactions.map((tx) => (
                  <div key={tx.id} className="transaction-item">
                    <div className="transaction-icon">
                      {tx.amount > 0 ? "↓" : "↑"}
                    </div>
                    <div className="transaction-details">
                      <span className="transaction-type">{TX_LABELS[tx.transaction_type] || tx.transaction_type}</span>
                      <span className="transaction-desc">{tx.description}</span>
                      <span className="transaction-date">{new Date(tx.created_at).toLocaleString()}</span>
                    </div>
                    <div className="transaction-amount-col">
                      <span className={`transaction-amount ${tx.amount > 0 ? "positive" : "negative"}`}>
                        {tx.amount > 0 ? "+" : ""}${Math.abs(tx.amount).toFixed(2)}
                      </span>
                      <span className="transaction-balance">Balance: ${tx.balance_after.toFixed(2)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {txTotal > 15 && (
              <div className="pagination">
                <button className="btn btn-sm btn-secondary" onClick={() => setTxPage((p) => Math.max(1, p - 1))} disabled={txPage === 1}>Previous</button>
                <span className="page-info">Page {txPage}</span>
                <button className="btn btn-sm btn-secondary" onClick={() => setTxPage((p) => p + 1)} disabled={transactions.length < 15}>Next</button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
