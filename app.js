async function getFrenchSentence() {
  const apiUrl = 'https://tatoeba.org/en/api_v0/search?from=fra&sort=random&limit=1&tags=francais';
  const proxyUrl = `https://corsproxy.io/?${encodeURIComponent(apiUrl)}`;

  try {
    const response = await fetch(proxyUrl);
    const data = await response.json();

    if (data.results && data.results.length > 0) {
      const phrase = data.results[0].text;
      document.getElementById("french-sentence").textContent = phrase;
      window.currentFrenchSentence = phrase;
    } else {
      document.getElementById("french-sentence").textContent = "Aucune phrase trouvée.";
    }
  } catch (error) {
    console.error("Erreur :", error.message);
    document.getElementById("french-sentence").textContent = "Erreur de chargement.";
  }
}

function submitTranslation() {
  const phrase = window.currentFrenchSentence || '';
  const translation = document.getElementById("comorian-translation").value;
  console.log("Phrase originale :", phrase);
  console.log("Traduction comorienne :", translation);
  alert("Traduction soumise ! (à connecter à la BDD plus tard)");
}

getFrenchSentence();
