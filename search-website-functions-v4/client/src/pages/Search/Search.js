import React, { useEffect, useState, useRef } from 'react';
import axios from 'axios';
import CircularProgress  from '@mui/material/CircularProgress';
import { useLocation, useNavigate } from "react-router-dom";

import Results from '../../components/Results/Results';
import Pager from '../../components/Pager/Pager';
import Facets from '../../components/Facets/Facets';
import SearchBar from '../../components/SearchBar/SearchBar';
import logo from '../../images/partselect.svg';
import "../../components/SearchBar/SearchBar.css"
import "./Search.css";
// import { searchResponse } from '../../components/TestResponse';

export default function Search() {
  
  let location = useLocation();
  const navigate = useNavigate();
  
  const [results, setResults] = useState([]);
  const [resultCount, setResultCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const qParam = new URLSearchParams(location.search).get('q') ?? "*";
  const topParam = parseInt(new URLSearchParams(location.search).get('top') ?? 8, 10);
  const skipParam = parseInt(new URLSearchParams(location.search).get('skip') ?? 0, 10);
  const [q, setQ] = useState(qParam);
  const [skip, setSkip] = useState(skipParam);
  const [top] = useState(topParam);
  const [filters, setFilters] = useState(undefined);
  const [facets, setFacets] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [preSelectedFilters, setPreSelectedFilters] = useState([]);
  const [preSelectedFlag, setPreSelectedFlag] = useState(false);
  const [keywords, setKeywords] = useState(q);
  const [resultFlag, setResultFlag] = useState(undefined);
  const [modelBrandName, setModelBrandName] = useState("");
  const [modelEquipmentType, setModelEquipmentType] = useState("");
  const resultsPerPage = top;
  const initialRef = useRef(true);
  useEffect(() => {
    if (initialRef.current && (top===topParam || skip===skipParam || q===qParam || filters===undefined)) {
      initialRef.current = false;
      return;
    }

    setIsLoading(true);
    const newSkip = (currentPage - 1) * top;
    if (skip !== newSkip) {
      setSkip(newSkip);
      return;
    }

    if (!preSelectedFlag && filters) {
      const body = {
        q: keywords,
        top: top,
        skip: skip,
        filters: filters,
      };
      axios.post('http://0.0.0.0:8000/search', body)
          .then(response => {
            setResults(response.data.results);
            setFacets(response.data.facets);
            setResultCount(response.data.count);
            if (response.data.preselectedFilters && response.data.preselectedFilters.length > 0) {
              setPreSelectedFilters(response.data.preselectedFilters);
              setPreSelectedFlag(true);
            }
            if (response.data.keywords.toLowerCase() !== q.toLowerCase()) {
              setKeywords(response.data.keywords);
            }
            setResultFlag(response.data.resultFlag);
            setModelBrandName(response.data.modelBrandName);
            setModelEquipmentType(response.data.modelEquipmentType);
            setIsLoading(false);
          })
          .catch(error => {
            console.error(error);
            setIsLoading(false);
          });
    } else {
      setPreSelectedFlag(false);
      setIsLoading(false);
    }
  }, [keywords, top, skip, filters, currentPage]);

  useEffect(() => {
    if (preSelectedFilters && preSelectedFilters.length > 0) {
      setFilters(preSelectedFilters);
      setPreSelectedFilters([]);
    }
  }, [preSelectedFilters]);

  useEffect(() => {
    setCurrentPage(1);
    setFilters([]);
    setKeywords(q);
    navigate('/search?q=' + q);
  }, [q]);

  let postSearchHandler = (searchTerm) => {
    if (!searchTerm || searchTerm === '') {
      searchTerm = '*'
    }
    setQ(searchTerm);
  }

  var body;
  if (isLoading) {
    body = (
      <div className="col-md-9">
        <CircularProgress />
      </div>);
  } else {
    body = (
      <div className="col-md-9">
        <Results documents={results} top={top} skip={skip} count={resultCount} q={q} keywords={keywords} setQ={setQ} filters={filters} resultFlag={resultFlag} modelBrandName={modelBrandName} modelEquipmentType={modelEquipmentType}></Results>
        <Pager className="pager-style" currentPage={currentPage} resultCount={resultCount} resultsPerPage={resultsPerPage} setCurrentPage={setCurrentPage}></Pager>
      </div>
    )
  }

  return (
    <div>
    <header className="header">
      <nav className="navbar navbar-expand-lg">
        <a className="navbar-brand" href="/">
          <img src={logo} height="50" className="navbar-logo" alt="PartSelect" />
        </a>
      </nav>
    </header>
    <div className="search-bar-container-searchpage">
      <div className="search-bar-searchpage">
      <SearchBar onSearchHandler={postSearchHandler} page="searchpage"></SearchBar>
      </div>
    </div>
    <main className="main main--search container-fluid">
      <div className="row">
        <div className="col-md-3"> 
          <Facets facets={facets} filters={filters} preSelectedFilters={preSelectedFilters} setFilters={setFilters}></Facets>
        </div>
        {body}
      </div>
    </main>
    </div>
  );
}
