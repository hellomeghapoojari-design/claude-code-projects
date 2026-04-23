import { redirect } from "next/navigation";

// Root redirects to /books
export default function Home() {
  redirect("/books");
}
