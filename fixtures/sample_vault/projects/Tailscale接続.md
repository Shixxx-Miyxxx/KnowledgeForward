# Tailscale 接続

iPhone Safari から使う場合は、Mac と iPhone を同じ Tailscale tailnet に参加させます。

## 起動

通常は localhost に bind して起動します。Tailscale 経由で公開するときだけ、Tailscale IP から到達できる bind 設定に変更します。

## 注意

Tailscale 経由でもトークン認証を使います。共有端末や信頼できないネットワークでは token を推測されにくい値に変更します。
