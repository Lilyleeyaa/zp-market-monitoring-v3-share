"""
비밀번호 해시 생성 도구
"""
import hashlib

def main():
    print("=" * 60)
    print("비밀번호 해시 생성기")
    print("=" * 60)
    print("\n공통 비밀번호를 입력하세요 (MNC_BD 공유용)")
    password = input("비밀번호: ")
    
    # SHA-256 해시 생성
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    print("\n" + "=" * 60)
    print("생성된 해시:")
    print("=" * 60)
    print(f"\ncommon_password_hash: \"{password_hash}\"")
    print("\n이 값을 auth/config.yaml 파일에 추가하세요.")
    print("=" * 60)

if __name__ == "__main__":
    main()
