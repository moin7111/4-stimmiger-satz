import type { NextAuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: "Admin",
      credentials: {
        password: { label: "Passwort", type: "password" },
      },
      async authorize(credentials): Promise<{ id: string; name: string } | null> {
        const adminPassword = process.env.ADMIN_PASSWORD;
        if (!adminPassword) {
          return null;
        }
        if (credentials?.password === adminPassword) {
          return { id: "admin", name: "Admin" };
        }
        return null;
      },
    }),
  ],
  secret: process.env.NEXTAUTH_SECRET,
  session: { strategy: "jwt" },
  pages: { signIn: "/admin/login" },
};

