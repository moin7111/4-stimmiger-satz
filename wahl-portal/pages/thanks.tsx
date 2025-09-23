export default function Thanks() {
  return (
    <div className="max-w-3xl mx-auto p-6 text-white">
      <h1 className="text-2xl font-bold mb-4">Vielen Dank!</h1>
      <p>
        Deine Wahl wurde erfolgreich eingereicht und kann auf der Webseite nicht mehr geändert werden. Bei Fragen oder Problemen wende dich bitte an deine Klassensprecherin bzw. deinen Klassensprecher.
      </p>
    </div>
  );
}

export function getServerSideProps() {
  return { props: {} };
}

