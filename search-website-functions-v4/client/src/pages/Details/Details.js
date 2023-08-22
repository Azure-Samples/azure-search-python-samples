import React, { useState, useEffect } from "react";
import { useParams } from 'react-router-dom';
import CircularProgress from '@mui/material/CircularProgress';
import axios from 'axios';

import "./Details.css";

export default function Details() {

  let { id } = useParams();
  const [document, setDocument] = useState({});
  const [selectedTab, setTab] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    axios.get('/api/lookup?id=' + id)
      .then(response => {
        const doc = response.data.document;
        setDocument(doc);
        setIsLoading(false);
      })
      .catch(error => {
        console.log(error);
        setIsLoading(false);
      });
  }, [id]);

  let detailsBody = (<CircularProgress />),
    resultStyle = "nav-link",
    rawStyle = "nav-link";

  if (!isLoading && document) {
    if (selectedTab === 0) {
      resultStyle += " active";
      detailsBody = (
        <div className="card-body">
          <h5 className="card-title">Titulo: {document.filename}</h5>
          <div className="text-justify">
            <p className="card-text">Autor: {document.author}</p>
            <p className="card-text">Last Modified: {document.last_modified_date}</p>
            <p className="card-text">Created: {document.created_date}</p>
            <p className="card-text">Pages: {document.number_of_pages}</p>
          </div>

          <p className="card-text">Content: {document.content}</p>
        </div>
      );
    }
    else {
      rawStyle += " active";
      detailsBody = (
        <div className="card-body text-left">
          <pre><code>
            {JSON.stringify(document, null, 2)}
          </code></pre>
        </div>
      );
    }
  }
  return (
    <main className="main main--details container fluid">
      <div className="card text-center result-container">
        <div className="card-header">
          <ul className="nav nav-tabs card-header-tabs">
            <li className="nav-item"><button className={resultStyle} onClick={() => setTab(0)}>Result</button></li>
            <li className="nav-item"><button className={rawStyle} onClick={() => setTab(1)}>Raw Data</button></li>
          </ul>
        </div>
        {detailsBody}
      </div>
    </main>
  );
}